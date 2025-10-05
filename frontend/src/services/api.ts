import axios, { AxiosInstance, AxiosResponse } from 'axios';
import {
  Story,
  Character,
  User,
  Episode,
  AggregationSummary,
  Snapshot,
  StoryCreateForm,
  CharacterUpdateForm,
  NotificationPreferences,
  ApiError,
} from '@/types/api';

// Create axios instance with base configuration
const api: AxiosInstance = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || '/api',
  timeout: 10000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor for auth tokens (if needed in future)
api.interceptors.request.use(
  (config) => {
    // Add auth token if available
    const token = localStorage.getItem('authToken');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Response interceptor for error handling
api.interceptors.response.use(
  (response: AxiosResponse) => {
    return response;
  },
  (error) => {
    // Handle network errors gracefully
    if (!error.response) {
      // Network error (server not available)
      const networkError: ApiError = {
        detail: 'Backend service is not available. Please start the backend server.',
        error_code: 'SERVICE_UNAVAILABLE'
      };
      console.warn('API Service unavailable:', error.message);
      return Promise.reject(networkError);
    }

    const apiError: ApiError = error.response?.data || {
      detail: 'An error occurred',
    };
    
    // Check if this is a service unavailable error from proxy
    if (error.response?.status === 503 || apiError.error_code === 'SERVICE_UNAVAILABLE') {
      console.warn('Backend service unavailable');
      return Promise.reject({
        detail: 'Backend service is not available. Please start the backend server on port 8000.',
        error_code: 'SERVICE_UNAVAILABLE'
      });
    }
    
    // Only show critical errors in console for actual API errors
    if (error.response?.status >= 500) {
      console.error('API Error:', apiError.detail);
    }
    
    return Promise.reject(apiError);
  }
);

// API Service Class
export class ApiService {
  // Story endpoints
  static async getStories(params?: {
    user_id?: string;
    status?: string;
    limit?: number;
    offset?: number;
  }): Promise<Story[]> {
    const { data } = await api.get('/stories', { params });
    return data;
  }

  static async getStory(id: string): Promise<Story> {
    const { data } = await api.get(`/stories/${id}`);
    return data;
  }

  static async createStory(story: StoryCreateForm): Promise<Story> {
    const { data } = await api.post('/stories', story);
    return data;
  }

  static async generateStoryNow(windowMinutes: number = 5): Promise<Story> {
    // Get recent aggregation summary and create quick story
    const summary = await this.getAggregationSummary(windowMinutes);
    
    const quickStory: StoryCreateForm = {
      title: `Live Story - ${new Date().toLocaleTimeString()}`,
      story_type: 'adventure',
      character_attributes: summary.characters.slice(0, 3).map(c => c.archetype),
      age_group: 'child',
      life_lessons: ['friendship'],
      episode_count: 1,
      prompt: `Generate a story based on recent bird activity: ${summary.species.join(', ')}`,
    };
    
    return this.createStory(quickStory);
  }

  static async publishEpisode(storyId: string, episodeIndex: number): Promise<Episode> {
    const { data } = await api.post(`/stories/${storyId}/episodes/${episodeIndex}/publish`);
    return data;
  }

  // Episode endpoints
  static async getEpisode(storyId: string, episodeIndex: number): Promise<Episode> {
    const { data } = await api.get(`/stories/${storyId}/episodes/${episodeIndex}`);
    return data;
  }

  // Character endpoints
  static async getCharacters(params?: {
    user_id?: string;
    species?: string;
    active_only?: boolean;
    limit?: number;
  }): Promise<Character[]> {
    const { data } = await api.get('/characters', { params });
    return data;
  }

  static async updateCharacter(id: string, updates: CharacterUpdateForm): Promise<Character> {
    const { data } = await api.patch(`/characters/${id}`, updates);
    return data;
  }

  static async mergeCharacters(sourceId: string, targetId: string): Promise<Character> {
    // This would need to be implemented in the backend
    const { data } = await api.post(`/characters/${targetId}/merge`, { source_id: sourceId });
    return data;
  }

  static async deleteCharacter(id: string): Promise<void> {
    await api.delete(`/characters/${id}`);
  }

  // User endpoints
  static async getUser(id: string): Promise<User> {
    const { data } = await api.get(`/users/${id}`);
    return data;
  }

  static async createUser(userData: { username: string; email: string; preferences?: any }): Promise<User> {
    const { data } = await api.post('/users', userData);
    return data;
  }

  static async updateUserPreferences(id: string, preferences: Partial<NotificationPreferences>): Promise<User> {
    const { data } = await api.patch(`/users/${id}/preferences`, preferences);
    return data;
  }

  // Aggregation endpoints
  static async getAggregationSummary(windowMinutes: number = 15): Promise<AggregationSummary> {
    const { data } = await api.get('/aggregator/summary', { 
      params: { window_minutes: windowMinutes } 
    });
    return data;
  }

  // Ingest endpoints
  static async triggerSampleCapture(params?: { 
    source_url?: string; 
    duration?: number; 
  }): Promise<{ success: boolean; sample_id: string }> {
    const { data } = await api.post('/ingest/sample', params || {});
    return data;
  }

  // Snapshot endpoints (assuming this will be implemented)
  static async getSnapshots(limit: number = 10): Promise<Snapshot[]> {
    try {
      const { data } = await api.get('/snapshots', { params: { limit } });
      return data;
    } catch (error) {
      // Return mock data for development
      return this.getMockSnapshots(limit);
    }
  }

  private static getMockSnapshots(limit: number): Snapshot[] {
    return Array.from({ length: limit }, (_, i) => ({
      id: `snapshot-${i + 1}`,
      image_url: `https://picsum.photos/400/300?random=${i + 1}`,
      timestamp: new Date(Date.now() - i * 60000).toISOString(),
      detections: [
        {
          species: ['Northern Cardinal', 'Blue Jay', 'American Robin', 'House Sparrow'][i % 4],
          confidence: 0.8 + Math.random() * 0.2,
        },
      ],
    }));
  }

  // Notification endpoints
  static async subscribeToNotifications(preferences: NotificationPreferences): Promise<void> {
    await api.post('/notifications/subscribe', preferences);
  }

  static async sendTestNotification(userId: string): Promise<void> {
    await api.post('/notifications/send', {
      user_id: userId,
      notification_type: 'test',
      title: 'Test Notification',
      message: 'This is a test notification from Birds with Friends!',
    });
  }

  // WebPush subscription
  static async subscribeToWebPush(subscription: PushSubscription): Promise<void> {
    await api.post('/notifications/webpush/subscribe', {
      endpoint: subscription.endpoint,
      keys: {
        p256dh: subscription.getKey('p256dh'),
        auth: subscription.getKey('auth'),
      },
    });
  }

  // Health check
  static async healthCheck(): Promise<{ status: string; services: Record<string, boolean> }> {
    const { data } = await api.get('/health');
    return data;
  }
}

export default api;