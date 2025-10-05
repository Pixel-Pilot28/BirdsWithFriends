import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from 'react-query';
import { BookOpen, Play, Calendar, Clock, Eye, Plus, X } from 'lucide-react';
import { ApiService } from '@/services/api';
import { Story, Episode } from '@/types/api';
import { formatDistanceToNow } from 'date-fns';
import StoryCreateModal from '@/components/StoryCreateModal';
import LoadingSpinner from '@/components/LoadingSpinner';

export default function StoriesPage() {
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [selectedEpisode, setSelectedEpisode] = useState<Episode | null>(null);
  const queryClient = useQueryClient();

  // Fetch stories
  const { data: stories, isLoading, isError } = useQuery<Story[]>(
    'stories',
    () => ApiService.getStories(),
    {
      refetchInterval: 30000, // Refresh every 30 seconds
      retry: false,
      refetchOnWindowFocus: false,
    }
  );

  // Publish episode mutation
  const publishEpisodeMutation = useMutation(
    ({ storyId, episodeIndex }: { storyId: string; episodeIndex: number }) =>
      ApiService.publishEpisode(storyId, episodeIndex),
    {
      onSuccess: () => {
        queryClient.invalidateQueries('stories');
      },
    }
  );

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'published':
        return 'bg-green-100 text-green-800';
      case 'scheduled':
        return 'bg-blue-100 text-blue-800';
      case 'draft':
        return 'bg-gray-100 text-gray-800';
      default:
        return 'bg-gray-100 text-gray-800';
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'published':
        return <Eye className="w-3 h-3" />;
      case 'scheduled':
        return <Calendar className="w-3 h-3" />;
      case 'draft':
        return <Clock className="w-3 h-3" />;
      default:
        return <Clock className="w-3 h-3" />;
    }
  };

  const handleEpisodeClick = async (story: Story, episodeIndex: number) => {
    try {
      const episode = await ApiService.getEpisode(story.id, episodeIndex);
      setSelectedEpisode(episode);
    } catch (error) {
      console.error('Failed to fetch episode:', error);
    }
  };

  const handlePublishNow = (storyId: string, episodeIndex: number) => {
    publishEpisodeMutation.mutate({ storyId, episodeIndex });
  };

  if (isLoading) {
    return (
      <div className="flex justify-center py-12">
        <LoadingSpinner />
      </div>
    );
  }

  if (isError) {
    return (
      <div className="space-y-8">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-display font-bold text-gray-900">Stories</h1>
            <p className="text-gray-600 mt-1">Manage your bird stories and episodes</p>
          </div>
          <button
            onClick={() => setShowCreateModal(true)}
            className="btn-primary flex items-center space-x-2"
          >
            <Plus className="w-4 h-4" />
            <span>New Story</span>
          </button>
        </div>
        
        <div className="card p-12 text-center">
          <BookOpen className="w-16 h-16 mx-auto mb-4 text-yellow-500 opacity-50" />
          <h3 className="text-lg font-medium text-gray-900 mb-2">
            Story service temporarily unavailable
          </h3>
          <p className="text-gray-600 mb-4">
            The backend service is starting up. You can still create new stories, but existing stories won't load until the service is running.
          </p>
          <button
            onClick={() => window.location.reload()}
            className="btn-secondary"
          >
            Try Again
          </button>
        </div>
        
        <StoryCreateModal
          isOpen={showCreateModal}
          onClose={() => setShowCreateModal(false)}
        />
      </div>
    );
  }

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-display font-bold text-gray-900">Stories</h1>
          <p className="text-gray-600 mt-1">
            Manage your bird stories and episodes
          </p>
        </div>
        <button
          onClick={() => setShowCreateModal(true)}
          className="btn-primary flex items-center space-x-2"
        >
          <Plus className="w-4 h-4" />
          <span>New Story</span>
        </button>
      </div>

      {/* Stories Grid */}
      {stories && stories.length > 0 ? (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {stories.map((story) => (
            <div key={story.id} className="card p-6">
              {/* Story Header */}
              <div className="flex items-start justify-between mb-4">
                <div className="flex-1">
                  <h3 className="text-lg font-semibold text-gray-900 mb-2">
                    {story.title}
                  </h3>
                  <div className="flex items-center space-x-4 text-sm text-gray-600">
                    <span className={`px-2 py-1 rounded-full text-xs font-medium flex items-center space-x-1 ${getStatusColor(story.status)}`}>
                      {getStatusIcon(story.status)}
                      <span className="capitalize">{story.status}</span>
                    </span>
                    <span>{story.story_type}</span>
                    <span>{story.age_group}</span>
                  </div>
                </div>
                <div className="text-sm text-gray-500">
                  {story.episode_count > 1 ? (
                    <span>{story.current_episode}/{story.episode_count} episodes</span>
                  ) : (
                    <span>Single episode</span>
                  )}
                </div>
              </div>

              {/* Story Metadata */}
              <div className="space-y-2 mb-4">
                <div className="text-sm text-gray-600">
                  <span className="font-medium">Life lessons:</span>{' '}
                  {story.life_lessons.join(', ')}
                </div>
                <div className="text-sm text-gray-600">
                  <span className="font-medium">Created:</span>{' '}
                  {formatDistanceToNow(new Date(story.created_at), { addSuffix: true })}
                </div>
                {story.scheduled_for && (
                  <div className="text-sm text-gray-600">
                    <span className="font-medium">Scheduled:</span>{' '}
                    {formatDistanceToNow(new Date(story.scheduled_for), { addSuffix: true })}
                  </div>
                )}
              </div>

              {/* Episodes Timeline */}
              {story.episode_count > 1 && (
                <div className="border-t pt-4">
                  <h4 className="text-sm font-medium text-gray-900 mb-3">Episodes</h4>
                  <div className="space-y-2">
                    {Array.from({ length: story.episode_count }, (_, index) => {
                      const episodeNumber = index + 1;
                      const isPublished = episodeNumber <= story.current_episode;
                      const isScheduled = episodeNumber === story.current_episode + 1;
                      
                      let episodeStatus: 'published' | 'scheduled' | 'draft';
                      if (isPublished) episodeStatus = 'published';
                      else if (isScheduled) episodeStatus = 'scheduled';
                      else episodeStatus = 'draft';

                      return (
                        <div
                          key={episodeNumber}
                          className="flex items-center justify-between p-3 bg-gray-50 rounded-lg"
                        >
                          <div className="flex items-center space-x-3">
                            <span className={`px-2 py-1 rounded text-xs font-medium flex items-center space-x-1 ${getStatusColor(episodeStatus)}`}>
                              {getStatusIcon(episodeStatus)}
                              <span>Episode {episodeNumber}</span>
                            </span>
                            {isPublished && (
                              <button
                                onClick={() => handleEpisodeClick(story, index)}
                                className="text-primary-600 hover:text-primary-700 text-sm font-medium"
                              >
                                Read
                              </button>
                            )}
                          </div>
                          {isScheduled && (
                            <button
                              onClick={() => handlePublishNow(story.id, index)}
                              disabled={publishEpisodeMutation.isLoading}
                              className="btn btn-xs bg-green-600 text-white hover:bg-green-700 flex items-center space-x-1"
                            >
                              <Play className="w-3 h-3" />
                              <span>Publish Now</span>
                            </button>
                          )}
                        </div>
                      );
                    })}
                  </div>
                </div>
              )}

              {/* Single Episode Actions */}
              {story.episode_count === 1 && (
                <div className="border-t pt-4 flex items-center justify-between">
                  <button
                    onClick={() => handleEpisodeClick(story, 0)}
                    className="btn-secondary text-sm"
                  >
                    Read Story
                  </button>
                  {story.status === 'draft' && (
                    <button
                      onClick={() => handlePublishNow(story.id, 0)}
                      disabled={publishEpisodeMutation.isLoading}
                      className="btn btn-sm bg-green-600 text-white hover:bg-green-700"
                    >
                      Publish Now
                    </button>
                  )}
                </div>
              )}
            </div>
          ))}
        </div>
      ) : (
        <div className="text-center py-12">
          <BookOpen className="w-12 h-12 text-gray-400 mx-auto mb-4" />
          <h3 className="text-lg font-medium text-gray-900 mb-2">No stories yet</h3>
          <p className="text-gray-600 mb-6">
            Create your first story from the live bird activity or start with a custom story.
          </p>
          <button
            onClick={() => setShowCreateModal(true)}
            className="btn-primary"
          >
            Create Your First Story
          </button>
        </div>
      )}

      {/* Modals */}
      <StoryCreateModal
        isOpen={showCreateModal}
        onClose={() => setShowCreateModal(false)}
      />

      {/* Episode Reader Modal */}
      {selectedEpisode && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-lg shadow-xl max-w-2xl w-full max-h-[80vh] overflow-hidden">
            <div className="flex items-center justify-between p-6 border-b">
              <h2 className="text-xl font-display font-semibold text-gray-900">
                {selectedEpisode.title}
              </h2>
              <button
                onClick={() => setSelectedEpisode(null)}
                className="w-8 h-8 flex items-center justify-center text-gray-400 hover:text-gray-600 rounded-lg hover:bg-gray-100"
              >
                <X className="w-5 h-5" />
              </button>
            </div>
            <div className="p-6 overflow-y-auto">
              <div className="prose max-w-none">
                {selectedEpisode.content.split('\n').map((paragraph, index) => (
                  <p key={index} className="mb-4 text-gray-700 leading-relaxed">
                    {paragraph}
                  </p>
                ))}
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}