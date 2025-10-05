// API Types for Birds with Friends Frontend

export interface Character {
  id: string;
  species: string;
  archetype: string;
  appearance_count: number;
  first_seen: string;
  last_seen: string;
  name?: string | null;
  notes?: string;
}

export interface Story {
  id: string;
  title: string;
  content: string;
  status: 'draft' | 'scheduled' | 'published';
  created_at: string;
  scheduled_for?: string | null;
  published_at?: string | null;
  user_id: string;
  episode_count: number;
  current_episode: number;
  story_type: string;
  age_group: string;
  life_lessons: string[];
  character_ids: string[];
}

export interface Episode {
  id: string;
  story_id: string;
  episode_number: number;
  title: string;
  content: string;
  status: 'draft' | 'scheduled' | 'published';
  scheduled_for?: string | null;
  published_at?: string | null;
  created_at: string;
}

export interface User {
  id: string;
  username: string;
  email: string;
  preferences: {
    email_notifications: boolean;
    webpush_notifications: boolean;
    sms_notifications?: boolean;
    [key: string]: any;
  };
  created_at: string;
  updated_at: string;
}

export interface NotificationPreferences {
  email_notifications: boolean;
  webpush_notifications: boolean;
  sms_notifications?: boolean;
  phone_number?: string;
  story_published: boolean;
  episode_published: boolean;
  character_updates: boolean;
}

export interface RecognitionEvent {
  species: string;
  confidence: number;
  timestamp: string;
  source_type: 'audio' | 'image';
  metadata: Record<string, any>;
}

export interface AggregationSummary {
  characters: Character[];
  species: string[];
  recent_activity: Array<{
    timestamp: string;
    source: string;
    species: string;
    confidence: number;
    character_id?: string;
  }>;
  timeframe: {
    start: string;
    end: string;
    window_minutes: string;
  };
}

export interface Snapshot {
  id: string;
  image_url: string;
  audio_url?: string;
  timestamp: string;
  detections: Array<{
    species: string;
    confidence: number;
    bounding_box?: {
      x: number;
      y: number;
      width: number;
      height: number;
    };
  }>;
}

// Form Types
export interface StoryCreateForm {
  title: string;
  story_type: string;
  character_attributes: string[];
  age_group: string;
  life_lessons: string[];
  episode_count: number;
  start_date?: string;
  frequency?: 'daily' | 'weekly' | 'monthly';
  prompt?: string;
}

export interface CharacterUpdateForm {
  archetype?: string;
  name?: string;
}

export interface UserUpdateForm {
  email?: string;
  preferences?: Partial<NotificationPreferences>;
}

// API Response Types
export interface ApiResponse<T = any> {
  success: boolean;
  message?: string;
  data?: T;
  error?: string;
}

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  per_page: number;
  pages: number;
}

// API Error Type
export interface ApiError {
  detail: string;
  error_code?: string;
  timestamp?: string;
}