import { useState } from 'react';
import { useQuery } from 'react-query';
import { Play, Camera, Zap, Clock } from 'lucide-react';
import { ApiService } from '@/services/api';
import { Snapshot } from '@/types/api';
import SnapshotCarousel from '@/components/SnapshotCarousel';
import StoryCreateModal from '@/components/StoryCreateModal';
import LoadingSpinner from '@/components/LoadingSpinner';

export default function LivePage() {
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [isGenerating, setIsGenerating] = useState(false);

  // Fetch snapshots
  const { data: snapshots, isLoading: snapshotsLoading, isError: snapshotsError } = useQuery<Snapshot[]>(
    'snapshots',
    () => ApiService.getSnapshots(10),
    {
      refetchInterval: 30000, // Refresh every 30 seconds
      retry: false, // Don't retry on network errors
      refetchOnWindowFocus: false, // Don't refetch on focus
    }
  );

  // Fetch aggregation summary
  const { data: summary, isLoading: summaryLoading, isError: summaryError } = useQuery(
    'aggregation-summary',
    () => ApiService.getAggregationSummary(15),
    {
      refetchInterval: 60000, // Refresh every minute
      retry: false, // Don't retry on network errors
      refetchOnWindowFocus: false, // Don't refetch on focus
    }
  );

  const handleGenerateStoryNow = async () => {
    setIsGenerating(true);
    try {
      await ApiService.generateStoryNow(5);
      // Could navigate to stories page or show success message
    } catch (error) {
      console.error('Failed to generate story:', error);
    } finally {
      setIsGenerating(false);
    }
  };

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="text-center">
        <h1 className="text-4xl font-display font-bold text-gray-900 mb-4">
          Live Bird Watching
        </h1>
        <p className="text-lg text-gray-600 max-w-2xl mx-auto">
          Watch the Cornell Lab feeder live and see AI-generated stories about our feathered friends
        </p>
      </div>

      {/* Live Stream Section */}
      <div className="card p-6">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-2xl font-display font-semibold text-gray-900">
            Cornell Lab Live Stream
          </h2>
          <div className="flex items-center space-x-2 text-sm text-green-600">
            <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse"></div>
            <span>Live</span>
          </div>
        </div>
        
        <div className="aspect-video bg-gray-900 rounded-lg overflow-hidden">
          <iframe
            src="https://www.youtube.com/embed/x10vL6_47Dw?autoplay=1&mute=1"
            title="Cornell Lab Bird Cam"
            className="w-full h-full"
            allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
            allowFullScreen
          />
        </div>
        
        <div className="mt-4 text-sm text-gray-600">
          <p>
            🎥 Live stream from the Cornell Lab of Ornithology FeederWatch Cam.
            Birds are detected in real-time and turned into magical stories!
          </p>
        </div>
      </div>

      {/* Quick Actions */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {/* Generate Story Now */}
        <div className="card p-6">
          <div className="flex items-center space-x-3 mb-4">
            <div className="w-10 h-10 bg-primary-100 rounded-lg flex items-center justify-center">
              <Zap className="w-5 h-5 text-primary-600" />
            </div>
            <h3 className="text-lg font-semibold text-gray-900">Generate Story Now</h3>
          </div>
          <p className="text-gray-600 mb-4">
            Create an instant story from the last 5 minutes of bird activity
          </p>
          <button
            onClick={handleGenerateStoryNow}
            disabled={isGenerating}
            className="btn-primary w-full flex items-center justify-center space-x-2"
          >
            {isGenerating ? (
              <LoadingSpinner size="sm" />
            ) : (
              <Play className="w-4 h-4" />
            )}
            <span>{isGenerating ? 'Generating...' : 'Generate Story'}</span>
          </button>
        </div>

        {/* Create Custom Story */}
        <div className="card p-6">
          <div className="flex items-center space-x-3 mb-4">
            <div className="w-10 h-10 bg-nature-100 rounded-lg flex items-center justify-center">
              <Camera className="w-5 h-5 text-nature-600" />
            </div>
            <h3 className="text-lg font-semibold text-gray-900">Custom Story</h3>
          </div>
          <p className="text-gray-600 mb-4">
            Create a personalized story with specific characters and themes
          </p>
          <button
            onClick={() => setShowCreateModal(true)}
            className="btn-secondary w-full"
          >
            Create Story
          </button>
        </div>

        {/* Recent Activity */}
        <div className="card p-6">
          <div className="flex items-center space-x-3 mb-4">
            <div className="w-10 h-10 bg-gray-100 rounded-lg flex items-center justify-center">
              <Clock className="w-5 h-5 text-gray-600" />
            </div>
            <h3 className="text-lg font-semibold text-gray-900">Recent Activity</h3>
          </div>
          {summaryLoading ? (
            <LoadingSpinner size="sm" />
          ) : summaryError ? (
            <div className="space-y-2">
              <p className="text-sm text-yellow-600">
                ⚠️ Activity data temporarily unavailable
              </p>
              <p className="text-xs text-gray-500">
                Backend service is starting up...
              </p>
            </div>
          ) : summary ? (
            <div className="space-y-2">
              <p className="text-sm text-gray-600">
                Species detected: {summary.species.length}
              </p>
              <p className="text-sm text-gray-600">
                Active characters: {summary.characters.length}
              </p>
              <p className="text-sm text-gray-600">
                Last 15 minutes: {summary.recent_activity.length} events
              </p>
            </div>
          ) : (
            <p className="text-sm text-gray-500">No recent activity</p>
          )}
        </div>
      </div>

      {/* Snapshot Carousel */}
      <div className="card p-6">
        <h2 className="text-2xl font-display font-semibold text-gray-900 mb-6">
          Recent Snapshots
        </h2>
        {snapshotsLoading ? (
          <div className="flex justify-center py-8">
            <LoadingSpinner />
          </div>
        ) : snapshotsError ? (
          <div className="text-center py-8 text-yellow-600">
            <Camera className="w-12 h-12 mx-auto mb-4 opacity-50" />
            <p className="font-medium">Snapshot service temporarily unavailable</p>
            <p className="text-sm text-gray-500 mt-2">
              The Cornell bird cam is still available above. Snapshots will appear when the backend service is running.
            </p>
          </div>
        ) : snapshots && snapshots.length > 0 ? (
          <SnapshotCarousel snapshots={snapshots} />
        ) : (
          <div className="text-center py-8 text-gray-500">
            <Camera className="w-12 h-12 mx-auto mb-4 opacity-50" />
            <p>No snapshots available yet</p>
            <p className="text-sm text-gray-400 mt-2">
              Snapshots will appear as birds visit the feeder
            </p>
          </div>
        )}
      </div>

      {/* Story Create Modal */}
      <StoryCreateModal
        isOpen={showCreateModal}
        onClose={() => setShowCreateModal(false)}
      />
    </div>
  );
}