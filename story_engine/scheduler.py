"""
Episode Release Scheduler - APScheduler-based scheduling for serialized stories.

Handles automated episode publishing on scheduled dates with retry logic,
duplicate prevention, and notification integration.
"""
import logging
from datetime import datetime, timezone, timedelta
from typing import Optional, List, Dict, Any
import asyncio
import pytz

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.jobstores.redis import RedisJobStore
from apscheduler.jobstores.memory import MemoryJobStore
from apscheduler.executors.asyncio import AsyncIOExecutor
from apscheduler.events import EVENT_JOB_EXECUTED, EVENT_JOB_ERROR
from sqlalchemy.orm import Session
from sqlalchemy import and_

from .database import get_db, Story, Episode, Base, engine
from .models import EpisodeStatus, ReleaseFrequency

logger = logging.getLogger(__name__)


class EpisodeScheduler:
    """Manages automated episode publishing for serialized stories."""
    
    def __init__(self, redis_url: str = "redis://localhost:6379/1"):
        """Initialize scheduler with Redis persistence."""
        
        # Configure job stores
        jobstores = {
            'default': RedisJobStore(host='localhost', port=6379, db=1),
            'memory': MemoryJobStore()
        }
        
        executors = {
            'default': AsyncIOExecutor(),
        }
        
        job_defaults = {
            'coalesce': True,  # Combine multiple pending executions into one
            'max_instances': 1,  # Prevent multiple instances of same job
            'misfire_grace_time': 300  # 5 minutes grace for missed executions
        }
        
        self.scheduler = AsyncIOScheduler(
            jobstores=jobstores,
            executors=executors,
            job_defaults=job_defaults
        )
        
        # Set up event listeners
        self.scheduler.add_listener(
            self._job_executed_listener,
            EVENT_JOB_EXECUTED | EVENT_JOB_ERROR
        )
        
        self._running = False
    
    async def start(self):
        """Start the scheduler."""
        if not self._running:
            self.scheduler.start()
            self._running = True
            logger.info("Episode scheduler started")
            
            # Schedule existing stories that need scheduling
            await self._reschedule_existing_stories()
    
    async def stop(self):
        """Stop the scheduler."""
        if self._running:
            self.scheduler.shutdown(wait=False)
            self._running = False
            logger.info("Episode scheduler stopped")
    
    async def schedule_story_episodes(
        self,
        story_id: str,
        start_date: datetime,
        release_frequency: ReleaseFrequency,
        user_timezone: str = "UTC"
    ) -> Dict[str, Any]:
        """Schedule all episodes for a story."""
        
        # Get database session
        db = next(get_db())
        
        try:
            # Get story details
            story = db.query(Story).filter(Story.id == story_id).first()
            if not story:
                raise ValueError(f"Story {story_id} not found")
            
            # Convert timezone
            tz = pytz.timezone(user_timezone)
            if start_date.tzinfo is None:
                start_date = tz.localize(start_date)
            else:
                start_date = start_date.astimezone(tz)
            
            # Update story scheduling info
            story.is_serialized = True
            story.start_date = start_date.astimezone(timezone.utc)
            story.release_frequency = release_frequency.value
            story.timezone = user_timezone
            
            # Calculate next release date
            next_release = self._calculate_next_release(start_date, release_frequency)
            story.next_release_at = next_release.astimezone(timezone.utc)
            
            # Get unpublished episodes
            episodes = db.query(Episode).filter(
                and_(
                    Episode.story_id == story_id,
                    Episode.status.in_(['draft', 'scheduled'])
                )
            ).order_by(Episode.episode_index).all()
            
            scheduled_count = 0
            current_release_time = next_release
            
            for episode in episodes:
                # Schedule this episode
                job_id = f"publish_episode_{story_id}_{episode.episode_index}"
                
                # Remove existing job if it exists
                if self.scheduler.get_job(job_id):
                    self.scheduler.remove_job(job_id)
                
                # Add new job
                self.scheduler.add_job(
                    self._publish_episode,
                    'date',
                    run_date=current_release_time,
                    args=[story_id, episode.episode_index],
                    id=job_id,
                    replace_existing=True,
                    jobstore='default'
                )
                
                # Update episode scheduling
                episode.status = EpisodeStatus.SCHEDULED.value
                episode.scheduled_for = current_release_time.astimezone(timezone.utc)
                
                scheduled_count += 1
                
                # Calculate next release time
                current_release_time = self._calculate_next_release(
                    current_release_time, release_frequency
                )
            
            db.commit()
            
            logger.info(f"Scheduled {scheduled_count} episodes for story {story_id}")
            
            return {
                "story_id": story_id,
                "episodes_scheduled": scheduled_count,
                "next_release": story.next_release_at.isoformat(),
                "release_frequency": release_frequency.value
            }
            
        except Exception as e:
            db.rollback()
            logger.error(f"Failed to schedule story {story_id}: {e}")
            raise
        finally:
            db.close()
    
    async def _publish_episode(self, story_id: str, episode_index: int):
        """Publish a specific episode (called by scheduler)."""
        
        db = next(get_db())
        
        try:
            # Get episode with database lock to prevent double-publishing
            episode = db.query(Episode).filter(
                and_(
                    Episode.story_id == story_id,
                    Episode.episode_index == episode_index,
                    Episode.status == EpisodeStatus.SCHEDULED.value
                )
            ).with_for_update().first()
            
            if not episode:
                logger.warning(f"Episode {story_id}/{episode_index} not found or not scheduled")
                return
            
            # Mark as published
            episode.status = EpisodeStatus.PUBLISHED.value
            episode.published_at = datetime.now(timezone.utc)
            
            # Update story progress
            story = db.query(Story).filter(Story.id == story_id).first()
            if story:
                story.completed_episodes += 1
                
                # Update next release date if there are more episodes
                remaining_episodes = db.query(Episode).filter(
                    and_(
                        Episode.story_id == story_id,
                        Episode.status == EpisodeStatus.SCHEDULED.value
                    )
                ).count()
                
                if remaining_episodes > 0:
                    # Calculate next release time
                    next_release = self._calculate_next_release(
                        datetime.now(timezone.utc),
                        ReleaseFrequency(story.release_frequency)
                    )
                    story.next_release_at = next_release
                else:
                    # No more episodes to schedule
                    story.next_release_at = None
            
            db.commit()
            
            logger.info(f"Published episode {episode_index} of story {story_id}")
            
            # Call notification routine
            await self._send_episode_notification(story_id, episode_index)
            
        except Exception as e:
            db.rollback()
            logger.error(f"Failed to publish episode {story_id}/{episode_index}: {e}")
            
            # Retry logic - reschedule for 1 hour later
            retry_time = datetime.now(timezone.utc) + timedelta(hours=1)
            job_id = f"publish_episode_{story_id}_{episode_index}"
            
            try:
                self.scheduler.add_job(
                    self._publish_episode,
                    'date',
                    run_date=retry_time,
                    args=[story_id, episode_index],
                    id=f"{job_id}_retry",
                    replace_existing=True,
                    jobstore='default'
                )
                logger.info(f"Rescheduled failed episode {story_id}/{episode_index} for {retry_time}")
            except Exception as retry_error:
                logger.error(f"Failed to reschedule episode: {retry_error}")
            
            raise
        finally:
            db.close()
    
    async def _send_episode_notification(self, story_id: str, episode_index: int):
        """Send notification that new episode is available."""
        # This would integrate with notification service
        # For now, just log it
        logger.info(f"📖 New episode published: Story {story_id}, Episode {episode_index}")
        
        # In a real implementation, this would:
        # - Send push notifications to subscribers
        # - Update user feeds
        # - Send email notifications
        # - Post to social media
        # - Update recommendation engines
    
    def _calculate_next_release(
        self,
        current_time: datetime,
        frequency: ReleaseFrequency
    ) -> datetime:
        """Calculate the next release time based on frequency."""
        
        if frequency == ReleaseFrequency.DAILY:
            return current_time + timedelta(days=1)
        elif frequency == ReleaseFrequency.WEEKLY:
            return current_time + timedelta(weeks=1)
        else:  # CUSTOM - default to daily
            return current_time + timedelta(days=1)
    
    async def _reschedule_existing_stories(self):
        """Reschedule any stories that have scheduled episodes but no active jobs."""
        
        db = next(get_db())
        
        try:
            # Find stories with scheduled episodes
            stories_with_scheduled = db.query(Story).filter(
                and_(
                    Story.is_serialized == True,
                    Story.next_release_at.isnot(None),
                    Story.next_release_at > datetime.now(timezone.utc)
                )
            ).all()
            
            for story in stories_with_scheduled:
                await self.schedule_story_episodes(
                    story.id,
                    story.start_date,
                    ReleaseFrequency(story.release_frequency),
                    story.timezone
                )
            
            logger.info(f"Rescheduled {len(stories_with_scheduled)} serialized stories")
            
        except Exception as e:
            logger.error(f"Failed to reschedule existing stories: {e}")
        finally:
            db.close()
    
    def _job_executed_listener(self, event):
        """Listen for job execution events."""
        if event.exception:
            logger.error(f"Job {event.job_id} crashed: {event.exception}")
        else:
            logger.debug(f"Job {event.job_id} executed successfully")
    
    async def cancel_story_schedule(self, story_id: str) -> Dict[str, Any]:
        """Cancel all scheduled episodes for a story."""
        
        db = next(get_db())
        
        try:
            # Get story
            story = db.query(Story).filter(Story.id == story_id).first()
            if not story:
                raise ValueError(f"Story {story_id} not found")
            
            # Remove scheduled jobs
            cancelled_jobs = 0
            episodes = db.query(Episode).filter(
                and_(
                    Episode.story_id == story_id,
                    Episode.status == EpisodeStatus.SCHEDULED.value
                )
            ).all()
            
            for episode in episodes:
                job_id = f"publish_episode_{story_id}_{episode.episode_index}"
                if self.scheduler.get_job(job_id):
                    self.scheduler.remove_job(job_id)
                    cancelled_jobs += 1
                
                # Reset episode status
                episode.status = EpisodeStatus.DRAFT.value
                episode.scheduled_for = None
            
            # Update story
            story.is_serialized = False
            story.next_release_at = None
            
            db.commit()
            
            logger.info(f"Cancelled {cancelled_jobs} scheduled episodes for story {story_id}")
            
            return {
                "story_id": story_id,
                "cancelled_jobs": cancelled_jobs,
                "status": "cancelled"
            }
            
        except Exception as e:
            db.rollback()
            logger.error(f"Failed to cancel schedule for story {story_id}: {e}")
            raise
        finally:
            db.close()
    
    def get_scheduled_jobs(self) -> List[Dict[str, Any]]:
        """Get all currently scheduled jobs."""
        jobs = []
        for job in self.scheduler.get_jobs():
            jobs.append({
                "id": job.id,
                "next_run": job.next_run_time.isoformat() if job.next_run_time else None,
                "args": job.args,
                "trigger": str(job.trigger)
            })
        return jobs


# Global scheduler instance
episode_scheduler = EpisodeScheduler()