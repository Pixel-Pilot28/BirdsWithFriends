import { useState } from 'react';
import { ChevronLeft, ChevronRight, Clock, Eye } from 'lucide-react';
import { Snapshot } from '@/types/api';
import { formatDistanceToNow } from 'date-fns';

interface SnapshotCarouselProps {
  snapshots: Snapshot[];
}

export default function SnapshotCarousel({ snapshots }: SnapshotCarouselProps) {
  const [currentIndex, setCurrentIndex] = useState(0);

  if (!snapshots || snapshots.length === 0) {
    return null;
  }

  const currentSnapshot = snapshots[currentIndex];

  const nextSnapshot = () => {
    setCurrentIndex((prev) => (prev + 1) % snapshots.length);
  };

  const prevSnapshot = () => {
    setCurrentIndex((prev) => (prev - 1 + snapshots.length) % snapshots.length);
  };

  const goToSnapshot = (index: number) => {
    setCurrentIndex(index);
  };

  return (
    <div className="space-y-4">
      {/* Main Image Display */}
      <div className="relative">
        <div className="aspect-video bg-gray-900 rounded-lg overflow-hidden">
          <img
            src={currentSnapshot.image_url}
            alt={`Bird snapshot ${currentIndex + 1}`}
            className="w-full h-full object-cover"
          />
          
          {/* Navigation Arrows */}
          {snapshots.length > 1 && (
            <>
              <button
                onClick={prevSnapshot}
                className="absolute left-4 top-1/2 -translate-y-1/2 w-10 h-10 bg-black/50 hover:bg-black/70 text-white rounded-full flex items-center justify-center transition-colors"
              >
                <ChevronLeft className="w-5 h-5" />
              </button>
              <button
                onClick={nextSnapshot}
                className="absolute right-4 top-1/2 -translate-y-1/2 w-10 h-10 bg-black/50 hover:bg-black/70 text-white rounded-full flex items-center justify-center transition-colors"
              >
                <ChevronRight className="w-5 h-5" />
              </button>
            </>
          )}
          
          {/* Image Info Overlay */}
          <div className="absolute bottom-4 left-4 right-4">
            <div className="bg-black/70 text-white rounded-lg p-3">
              <div className="flex items-center justify-between">
                <div className="flex items-center space-x-2 text-sm">
                  <Clock className="w-4 h-4" />
                  <span>
                    {formatDistanceToNow(new Date(currentSnapshot.timestamp), { addSuffix: true })}
                  </span>
                </div>
                <div className="text-sm">
                  {currentIndex + 1} of {snapshots.length}
                </div>
              </div>
              
              {currentSnapshot.detections.length > 0 && (
                <div className="mt-2">
                  <div className="flex items-center space-x-2 text-sm">
                    <Eye className="w-4 h-4" />
                    <span>Detected:</span>
                  </div>
                  <div className="mt-1 space-y-1">
                    {currentSnapshot.detections.map((detection, idx) => (
                      <div key={idx} className="text-sm">
                        <span className="font-medium">{detection.species}</span>
                        <span className="text-gray-300 ml-2">
                          ({Math.round(detection.confidence * 100)}% confidence)
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Thumbnail Navigation */}
      {snapshots.length > 1 && (
        <div className="flex space-x-2 overflow-x-auto pb-2">
          {snapshots.map((snapshot, index) => (
            <button
              key={snapshot.id}
              onClick={() => goToSnapshot(index)}
              className={`flex-shrink-0 w-16 h-12 rounded-md overflow-hidden border-2 transition-colors ${
                index === currentIndex
                  ? 'border-primary-500'
                  : 'border-gray-200 hover:border-gray-300'
              }`}
            >
              <img
                src={snapshot.image_url}
                alt={`Thumbnail ${index + 1}`}
                className="w-full h-full object-cover"
              />
            </button>
          ))}
        </div>
      )}

      {/* Auto-advance indicator */}
      <div className="flex justify-center">
        <div className="text-xs text-gray-500">
          🔄 Updates automatically every 30 seconds
        </div>
      </div>
    </div>
  );
}