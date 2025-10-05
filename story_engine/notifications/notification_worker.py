"""
Notification worker for handling episode publishing notifications.

Manages notification delivery with retry logic, exponential backoff,
and comprehensive error handling for both email and web push notifications.
"""
import logging
import asyncio
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any, Optional
import json

from sqlalchemy.orm import Session
from sqlalchemy import and_

from ..database import (
    get_db, SessionLocal, NotificationPreferencesDB, 
    PushSubscriptionDB, NotificationLogDB, Story, Episode
)
from ..models import NotificationType, NotificationStatus
from .email_sender import email_sender
from .webpush_sender import webpush_sender

logger = logging.getLogger(__name__)


class NotificationWorker:
    """Background worker for processing notification delivery."""
    
    def __init__(self, max_retries: int = 3, base_delay: float = 1.0):
        """Initialize notification worker."""
        self.max_retries = max_retries
        self.base_delay = base_delay  # Base delay in seconds for exponential backoff
        self.running = False
    
    async def start(self):
        """Start the notification worker."""
        self.running = True
        logger.info("Notification worker started")
    
    async def stop(self):
        """Stop the notification worker."""
        self.running = False
        logger.info("Notification worker stopped")
    
    async def send_episode_notifications(
        self,
        story_id: str,
        episode_index: int,
        user_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Send notifications for a published episode.
        
        If user_id is provided, only send to that user.
        Otherwise, send to all users with notification preferences.
        """
        
        db = SessionLocal()
        
        try:
            # Get story and episode information
            story = db.query(Story).filter(Story.id == story_id).first()
            if not story:
                raise ValueError(f"Story {story_id} not found")
            
            episode = db.query(Episode).filter(
                and_(
                    Episode.story_id == story_id,
                    Episode.episode_index == episode_index
                )
            ).first()
            if not episode:
                raise ValueError(f"Episode {story_id}/{episode_index} not found")
            
            # Get users to notify
            if user_id:
                # Single user notification
                preferences = db.query(NotificationPreferencesDB).filter(
                    NotificationPreferencesDB.user_id == user_id
                ).first()
                users_to_notify = [preferences] if preferences else []
            else:
                # All users with notification preferences enabled
                users_to_notify = db.query(NotificationPreferencesDB).filter(
                    and_(
                        NotificationPreferencesDB.email_notifications == True,
                        NotificationPreferencesDB.webpush_notifications == True
                    )
                ).all()
            
            results = {
                "story_id": story_id,
                "episode_index": episode_index,
                "notifications_sent": 0,
                "email_sent": 0,
                "webpush_sent": 0,
                "errors": []
            }
            
            # Send notifications to each user
            for user_prefs in users_to_notify:
                try:
                    # Send email notification
                    if user_prefs.email_notifications and user_prefs.email_address:
                        await self._send_email_notification(
                            db=db,
                            user_prefs=user_prefs,
                            story=story,
                            episode=episode
                        )
                        results["email_sent"] += 1
                    
                    # Send web push notifications
                    if user_prefs.webpush_notifications:
                        push_count = await self._send_webpush_notifications(
                            db=db,
                            user_prefs=user_prefs,
                            story=story,
                            episode=episode
                        )
                        results["webpush_sent"] += push_count
                    
                    results["notifications_sent"] += 1
                    
                except Exception as e:
                    error_msg = f"Failed to notify user {user_prefs.user_id}: {e}"
                    logger.error(error_msg)
                    results["errors"].append(error_msg)
            
            logger.info(f"Episode notifications completed: {results['notifications_sent']} users notified")
            return results
            
        except Exception as e:
            logger.error(f"Episode notification batch failed: {e}")
            raise
        finally:
            db.close()
    
    async def _send_email_notification(
        self,
        db: Session,
        user_prefs: NotificationPreferencesDB,
        story: Story,
        episode: Episode
    ):
        """Send email notification with retry logic."""
        
        notification_log = NotificationLogDB(
            user_id=user_prefs.user_id,
            story_id=story.id,
            episode_index=episode.episode_index,
            notification_type=NotificationType.EMAIL.value,
            status=NotificationStatus.PENDING.value
        )
        db.add(notification_log)
        db.commit()
        
        attempt = 0
        while attempt < self.max_retries:
            try:
                # Send email
                result = await email_sender.send_episode_notification(
                    user_email=user_prefs.email_address,
                    story_title=story.title,
                    episode_title=episode.title or f"Episode {episode.episode_index}",
                    episode_index=episode.episode_index,
                    story_id=story.id,
                    episode_summary=episode.summary or ""
                )
                
                if result["success"]:
                    # Success
                    notification_log.status = NotificationStatus.SENT.value
                    notification_log.sent_at = datetime.now(timezone.utc)
                    notification_log.attempts = attempt + 1
                    db.commit()
                    
                    logger.info(f"📧 Email notification sent to user {user_prefs.user_id}")
                    return
                else:
                    raise Exception(result.get("error", "Email sending failed"))
            
            except Exception as e:
                attempt += 1
                notification_log.attempts = attempt
                notification_log.error_message = str(e)
                
                if attempt >= self.max_retries:
                    # Max retries exceeded
                    notification_log.status = NotificationStatus.FAILED.value
                    notification_log.updated_at = datetime.now(timezone.utc)
                    db.commit()
                    
                    logger.error(f"Email notification failed after {attempt} attempts for user {user_prefs.user_id}: {e}")
                    raise
                else:
                    # Retry with exponential backoff
                    notification_log.status = NotificationStatus.RETRYING.value
                    notification_log.updated_at = datetime.now(timezone.utc)
                    db.commit()
                    
                    delay = self.base_delay * (2 ** (attempt - 1))
                    logger.warning(f"Email notification attempt {attempt} failed for user {user_prefs.user_id}, retrying in {delay}s: {e}")
                    await asyncio.sleep(delay)
    
    async def _send_webpush_notifications(
        self,
        db: Session,
        user_prefs: NotificationPreferencesDB,
        story: Story,
        episode: Episode
    ) -> int:
        """Send web push notifications to all user's subscriptions."""
        
        # Get all push subscriptions for user
        subscriptions = db.query(PushSubscriptionDB).filter(
            PushSubscriptionDB.user_id == user_prefs.user_id
        ).all()
        
        sent_count = 0
        
        for subscription in subscriptions:
            notification_log = NotificationLogDB(
                user_id=user_prefs.user_id,
                story_id=story.id,
                episode_index=episode.episode_index,
                notification_type=NotificationType.WEBPUSH.value,
                status=NotificationStatus.PENDING.value
            )
            db.add(notification_log)
            db.commit()
            
            attempt = 0
            while attempt < self.max_retries:
                try:
                    # Prepare subscription info
                    subscription_info = {
                        "endpoint": subscription.endpoint,
                        "keys": {
                            "p256dh": subscription.p256dh_key,
                            "auth": subscription.auth_key
                        }
                    }
                    
                    # Send web push
                    result = await webpush_sender.send_episode_notification(
                        subscription_info=subscription_info,
                        story_title=story.title,
                        episode_title=episode.title or f"Episode {episode.episode_index}",
                        episode_index=episode.episode_index,
                        story_id=story.id
                    )
                    
                    if result["success"]:
                        # Success
                        notification_log.status = NotificationStatus.SENT.value
                        notification_log.sent_at = datetime.now(timezone.utc)
                        notification_log.attempts = attempt + 1
                        db.commit()
                        
                        sent_count += 1
                        logger.info(f"🔔 Web push sent to user {user_prefs.user_id}")
                        break
                    else:
                        # Handle subscription expiration
                        if result.get("should_remove_subscription"):
                            logger.info(f"Removing expired push subscription for user {user_prefs.user_id}")
                            db.delete(subscription)
                            notification_log.status = NotificationStatus.FAILED.value
                            notification_log.error_message = "Subscription expired"
                            db.commit()
                            break
                        
                        raise Exception(result.get("error_message", "Web push failed"))
                
                except Exception as e:
                    attempt += 1
                    notification_log.attempts = attempt
                    notification_log.error_message = str(e)
                    
                    if attempt >= self.max_retries:
                        # Max retries exceeded
                        notification_log.status = NotificationStatus.FAILED.value
                        notification_log.updated_at = datetime.now(timezone.utc)
                        db.commit()
                        
                        logger.error(f"Web push failed after {attempt} attempts for user {user_prefs.user_id}: {e}")
                        break
                    else:
                        # Retry with exponential backoff
                        notification_log.status = NotificationStatus.RETRYING.value
                        notification_log.updated_at = datetime.now(timezone.utc)
                        db.commit()
                        
                        delay = self.base_delay * (2 ** (attempt - 1))
                        logger.warning(f"Web push attempt {attempt} failed for user {user_prefs.user_id}, retrying in {delay}s: {e}")
                        await asyncio.sleep(delay)
        
        return sent_count
    
    async def retry_failed_notifications(self) -> Dict[str, Any]:
        """Retry notifications that previously failed."""
        
        db = SessionLocal()
        
        try:
            # Get failed notifications from last 24 hours
            cutoff_time = datetime.now(timezone.utc) - timedelta(hours=24)
            
            failed_notifications = db.query(NotificationLogDB).filter(
                and_(
                    NotificationLogDB.status == NotificationStatus.FAILED.value,
                    NotificationLogDB.created_at > cutoff_time,
                    NotificationLogDB.attempts < self.max_retries
                )
            ).all()
            
            results = {
                "retried_count": 0,
                "success_count": 0,
                "still_failed_count": 0
            }
            
            for log_entry in failed_notifications:
                try:
                    # Re-send based on notification type
                    if log_entry.notification_type == NotificationType.EMAIL.value:
                        await self._retry_email_notification(db, log_entry)
                    elif log_entry.notification_type == NotificationType.WEBPUSH.value:
                        await self._retry_webpush_notification(db, log_entry)
                    
                    results["retried_count"] += 1
                    
                    if log_entry.status == NotificationStatus.SENT.value:
                        results["success_count"] += 1
                    else:
                        results["still_failed_count"] += 1
                
                except Exception as e:
                    logger.error(f"Retry failed for notification {log_entry.id}: {e}")
                    results["still_failed_count"] += 1
            
            logger.info(f"Notification retry completed: {results}")
            return results
            
        except Exception as e:
            logger.error(f"Notification retry batch failed: {e}")
            raise
        finally:
            db.close()
    
    async def _retry_email_notification(self, db: Session, log_entry: NotificationLogDB):
        """Retry a specific email notification."""
        # Implementation would re-send the email notification
        # Similar to _send_email_notification but for retry
        pass
    
    async def _retry_webpush_notification(self, db: Session, log_entry: NotificationLogDB):
        """Retry a specific web push notification."""
        # Implementation would re-send the web push notification
        # Similar to _send_webpush_notifications but for retry
        pass


# Global notification worker instance
notification_worker = NotificationWorker()