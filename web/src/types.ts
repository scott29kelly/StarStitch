// ====================
// Core Application Types
// ====================

export interface Subject {
  id: string;
  name: string;
  visual_prompt: string;
  image_url?: string;
  status: 'pending' | 'generating' | 'completed' | 'error';
}

export interface ProjectConfig {
  project_name: string;
  output_folder: string;
  settings: {
    aspect_ratio: '9:16' | '16:9' | '1:1';
    transition_duration_sec: number;
    image_model: string;
    video_model: string;
  };
  global_scene: {
    location_prompt: string;
    negative_prompt: string;
  };
  sequence: Subject[];
}

export interface RenderProgress {
  status: 'idle' | 'preparing' | 'rendering' | 'complete' | 'error';
  current_step: number;
  total_steps: number;
  current_subject?: string;
  progress_percent: number;
  message: string;
  elapsed_time: number;
}

export type View = 'dashboard' | 'configure' | 'render' | 'gallery';

// ====================
// API Request/Response Types
// ====================

export interface SubjectConfig {
  id?: string;
  name: string;
  visual_prompt: string;
}

export interface GlobalSceneConfig {
  location_prompt: string;
  negative_prompt: string;
}

export interface AudioConfig {
  enabled: boolean;
  audio_path: string;
  volume: number;
  fade_in_sec: number;
  fade_out_sec: number;
  loop: boolean;
  normalize: boolean;
}

export interface SettingsConfig {
  aspect_ratio: string;
  transition_duration_sec: number;
  image_model: string;
  video_model: string;
  variants: string[];
}

export interface RenderRequest {
  project_name: string;
  output_folder: string;
  settings: SettingsConfig;
  global_scene: GlobalSceneConfig;
  audio: AudioConfig;
  sequence: SubjectConfig[];
}

export type RenderStatusType = 'pending' | 'running' | 'complete' | 'error' | 'cancelled';

export interface RenderResponse {
  id: string;
  status: RenderStatusType;
  project_name: string;
  created_at: string;
  updated_at: string;
  current_step: number;
  total_steps: number;
  progress_percent: number;
  current_phase: string;
  message: string;
  output_path?: string;
  error?: string;
  elapsed_seconds: number;
}

export interface RenderListResponse {
  renders: RenderResponse[];
  total: number;
}

// ====================
// WebSocket Event Types
// ====================

export type ProgressEventType =
  | 'connected'
  | 'disconnected'
  | 'job_started'
  | 'job_completed'
  | 'job_failed'
  | 'job_cancelled'
  | 'phase_started'
  | 'phase_completed'
  | 'step_started'
  | 'step_progress'
  | 'step_completed'
  | 'progress'
  | 'log'
  | 'error';

export interface ProgressEvent {
  type: ProgressEventType;
  job_id: string;
  timestamp: string;
  current_step?: number;
  total_steps?: number;
  progress_percent?: number;
  phase?: string;
  subject?: string;
  message: string;
  data?: Record<string, unknown>;
}

// ====================
// Template Types
// ====================

export interface TemplateResponse {
  name: string;
  display_name: string;
  description: string;
  category: string;
  thumbnail?: string;
  tags: string[];
  author: string;
  version: string;
  base_config: Record<string, unknown>;
}

export interface TemplateListResponse {
  templates: TemplateResponse[];
  total: number;
  categories: CategoryResponse[];
}

export interface CategoryResponse {
  name: string;
  count: number;
}

// ====================
// Gallery Types
// ====================

export interface GalleryProject {
  id: string;
  name: string;
  date: string;
  duration: string;
  subjects: number;
  status: 'complete' | 'draft' | 'error';
  output_path?: string;
}
