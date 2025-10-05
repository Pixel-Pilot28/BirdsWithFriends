import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from 'react-query';
import { useForm, Controller } from 'react-hook-form';
import Select from 'react-select';
import DatePicker from 'react-datepicker';
import { X, BookOpen, Zap } from 'lucide-react';
import { ApiService } from '@/services/api';
import { StoryCreateForm, Character } from '@/types/api';
import LoadingSpinner from './LoadingSpinner';

interface StoryCreateModalProps {
  isOpen: boolean;
  onClose: () => void;
}

// Form options
const storyTypes = [
  { value: 'adventure', label: 'Adventure' },
  { value: 'friendship', label: 'Friendship' },
  { value: 'learning', label: 'Learning' },
  { value: 'mystery', label: 'Mystery' },
  { value: 'comedy', label: 'Comedy' },
];

const ageGroups = [
  { value: 'child', label: 'Children (3-8 years)' },
  { value: 'youth', label: 'Youth (9-14 years)' },
  { value: 'teen', label: 'Teen (15-17 years)' },
  { value: 'adult', label: 'Adult (18+ years)' },
  { value: 'all', label: 'All Ages' },
];

const lifeLessonsOptions = [
  { value: 'friendship', label: 'Friendship' },
  { value: 'sharing', label: 'Sharing' },
  { value: 'kindness', label: 'Kindness' },
  { value: 'perseverance', label: 'Perseverance' },
  { value: 'teamwork', label: 'Teamwork' },
  { value: 'honesty', label: 'Honesty' },
  { value: 'courage', label: 'Courage' },
  { value: 'patience', label: 'Patience' },
  { value: 'empathy', label: 'Empathy' },
  { value: 'responsibility', label: 'Responsibility' },
];

const frequencyOptions = [
  { value: 'daily', label: 'Daily' },
  { value: 'weekly', label: 'Weekly' },
  { value: 'monthly', label: 'Monthly' },
];

export default function StoryCreateModal({ isOpen, onClose }: StoryCreateModalProps) {
  const queryClient = useQueryClient();
  const [activeTab, setActiveTab] = useState<'basic' | 'advanced'>('basic');

  const {
    register,
    handleSubmit,
    control,
    watch,
    reset,
    formState: { errors },
  } = useForm<StoryCreateForm>({
    defaultValues: {
      title: '',
      story_type: 'adventure',
      character_attributes: [],
      age_group: 'child',
      life_lessons: [],
      episode_count: 1,
      start_date: undefined,
      frequency: undefined,
    },
  });

  const episodeCount = watch('episode_count');

  // Fetch available characters
  const { data: characters } = useQuery<Character[]>(
    'characters',
    () => ApiService.getCharacters({ active_only: true }),
    { enabled: isOpen }
  );

  // Create character attribute options from available characters
  const characterAttributeOptions = characters
    ? [...new Set(characters.map(c => c.archetype))].map(archetype => ({
        value: archetype,
        label: archetype,
      }))
    : [];

  // Create story mutation
  const createStoryMutation = useMutation(
    (data: StoryCreateForm) => ApiService.createStory(data),
    {
      onSuccess: () => {
        queryClient.invalidateQueries('stories');
        reset();
        onClose();
      },
    }
  );

  const onSubmit = (data: StoryCreateForm) => {
    createStoryMutation.mutate(data);
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-lg shadow-xl max-w-2xl w-full max-h-[90vh] overflow-hidden">
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b">
          <div className="flex items-center space-x-3">
            <div className="w-10 h-10 bg-primary-100 rounded-lg flex items-center justify-center">
              <BookOpen className="w-5 h-5 text-primary-600" />
            </div>
            <h2 className="text-xl font-display font-semibold text-gray-900">
              Create New Story
            </h2>
          </div>
          <button
            onClick={onClose}
            className="w-8 h-8 flex items-center justify-center text-gray-400 hover:text-gray-600 rounded-lg hover:bg-gray-100"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Tab Navigation */}
        <div className="flex border-b">
          <button
            onClick={() => setActiveTab('basic')}
            className={`flex-1 py-3 px-4 text-sm font-medium ${
              activeTab === 'basic'
                ? 'text-primary-600 border-b-2 border-primary-600'
                : 'text-gray-500 hover:text-gray-700'
            }`}
          >
            Basic Settings
          </button>
          <button
            onClick={() => setActiveTab('advanced')}
            className={`flex-1 py-3 px-4 text-sm font-medium ${
              activeTab === 'advanced'
                ? 'text-primary-600 border-b-2 border-primary-600'
                : 'text-gray-500 hover:text-gray-700'
            }`}
          >
            Advanced Settings
          </button>
        </div>

        {/* Form Content */}
        <form onSubmit={handleSubmit(onSubmit)} className="p-6 space-y-6 overflow-y-auto max-h-[60vh]">
          {activeTab === 'basic' && (
            <>
              {/* Title */}
              <div>
                <label className="form-label">Story Title</label>
                <input
                  type="text"
                  {...register('title')}
                  className="form-input"
                  placeholder="Enter a captivating title..."
                />
                {errors.title && <p className="form-error">{errors.title.message}</p>}
              </div>

              {/* Story Type */}
              <div>
                <label className="form-label">Story Type</label>
                <Controller
                  name="story_type"
                  control={control}
                  render={({ field }) => (
                    <Select
                      {...field}
                      options={storyTypes}
                      value={storyTypes.find(option => option.value === field.value)}
                      onChange={(option) => field.onChange(option?.value)}
                      placeholder="Select story type..."
                    />
                  )}
                />
                {errors.story_type && <p className="form-error">{errors.story_type.message}</p>}
              </div>

              {/* Character Attributes */}
              <div>
                <label className="form-label">Character Attributes</label>
                <Controller
                  name="character_attributes"
                  control={control}
                  render={({ field }) => (
                    <Select
                      {...field}
                      options={characterAttributeOptions}
                      value={characterAttributeOptions.filter(option => 
                        field.value?.includes(option.value)
                      )}
                      onChange={(options) => 
                        field.onChange(options?.map(option => option.value) || [])
                      }
                      isMulti
                      placeholder="Select character attributes..."
                    />
                  )}
                />
                {errors.character_attributes && (
                  <p className="form-error">{errors.character_attributes.message}</p>
                )}
              </div>

              {/* Age Group */}
              <div>
                <label className="form-label">Age Group</label>
                <Controller
                  name="age_group"
                  control={control}
                  render={({ field }) => (
                    <Select
                      {...field}
                      options={ageGroups}
                      value={ageGroups.find(option => option.value === field.value)}
                      onChange={(option) => field.onChange(option?.value)}
                      placeholder="Select age group..."
                    />
                  )}
                />
                {errors.age_group && <p className="form-error">{errors.age_group.message}</p>}
              </div>

              {/* Life Lessons */}
              <div>
                <label className="form-label">Life Lessons</label>
                <Controller
                  name="life_lessons"
                  control={control}
                  render={({ field }) => (
                    <Select
                      {...field}
                      options={lifeLessonsOptions}
                      value={lifeLessonsOptions.filter(option => 
                        field.value?.includes(option.value)
                      )}
                      onChange={(options) => 
                        field.onChange(options?.map(option => option.value) || [])
                      }
                      isMulti
                      placeholder="Select life lessons to include..."
                    />
                  )}
                />
                {errors.life_lessons && <p className="form-error">{errors.life_lessons.message}</p>}
              </div>
            </>
          )}

          {activeTab === 'advanced' && (
            <>
              {/* Episode Count */}
              <div>
                <label className="form-label">Number of Episodes</label>
                <input
                  type="number"
                  min="1"
                  max="10"
                  {...register('episode_count', { valueAsNumber: true })}
                  className="form-input"
                />
                {errors.episode_count && <p className="form-error">{errors.episode_count.message}</p>}
              </div>

              {/* Scheduling (only if multiple episodes) */}
              {episodeCount > 1 && (
                <>
                  <div>
                    <label className="form-label">Start Date (Optional)</label>
                    <Controller
                      name="start_date"
                      control={control}
                      render={({ field }) => (
                        <DatePicker
                          selected={field.value ? new Date(field.value) : null}
                          onChange={(date) => field.onChange(date?.toISOString())}
                          showTimeSelect
                          dateFormat="Pp"
                          className="form-input w-full"
                          placeholderText="Select start date and time..."
                          minDate={new Date()}
                        />
                      )}
                    />
                  </div>

                  <div>
                    <label className="form-label">Publishing Frequency</label>
                    <Controller
                      name="frequency"
                      control={control}
                      render={({ field }) => (
                        <Select
                          {...field}
                          options={frequencyOptions}
                          value={frequencyOptions.find(option => option.value === field.value)}
                          onChange={(option) => field.onChange(option?.value)}
                          placeholder="Select publishing frequency..."
                          isClearable
                        />
                      )}
                    />
                  </div>
                </>
              )}

              {/* Custom Prompt */}
              <div>
                <label className="form-label">Custom Prompt (Optional)</label>
                <textarea
                  {...register('prompt')}
                  rows={4}
                  className="form-input"
                  placeholder="Add any specific instructions or themes for the story..."
                />
              </div>
            </>
          )}
        </form>

        {/* Footer */}
        <div className="flex items-center justify-between p-6 border-t bg-gray-50">
          <div className="text-sm text-gray-600">
            {episodeCount === 1 ? (
              <span>📖 Single episode story</span>
            ) : (
              <span>📚 {episodeCount} episode series</span>
            )}
          </div>
          <div className="flex items-center space-x-3">
            <button
              type="button"
              onClick={onClose}
              className="btn-secondary"
            >
              Cancel
            </button>
            <button
              onClick={handleSubmit(onSubmit)}
              disabled={createStoryMutation.isLoading}
              className="btn-primary flex items-center space-x-2"
            >
              {createStoryMutation.isLoading ? (
                <LoadingSpinner size="sm" />
              ) : (
                <Zap className="w-4 h-4" />
              )}
              <span>
                {createStoryMutation.isLoading ? 'Creating...' : 'Create Story'}
              </span>
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}