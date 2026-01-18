export interface Subject {
  id: string;
  name: string;
  visual_prompt: string;
  image_url?: string;
  status: 'pending' | 'generating' | 'completed' | 'error';
}

export interface AudioSettings {
  enabled: boolean;
  audio_path: string;
  volume: number;
  fade_in_sec: number;
  fade_out_sec: number;
  loop: boolean;
  normalize: boolean;
}

export interface ProjectConfig {
  project_name: string;
  output_folder: string;
  settings: {
    aspect_ratio: '9:16' | '16:9' | '1:1';
    transition_duration_sec: number;
    image_model: string;
    video_model: string;
    variants?: string[];
  };
  global_scene: {
    location_prompt: string;
    negative_prompt: string;
  };
  sequence: Subject[];
  audio?: AudioSettings;
}

export interface RenderProgress {
  status: 'idle' | 'preparing' | 'rendering' | 'complete' | 'error' | 'cancelled';
  current_step: number;
  total_steps: number;
  current_subject?: string;
  progress_percent: number;
  message: string;
  elapsed_time: number;
  estimated_remaining?: number;
}

export type JobState = 'pending' | 'running' | 'complete' | 'failed' | 'cancelled';

export interface RenderJob {
  job_id: string;
  project_name: string;
  state: JobState;
  created_at: string;
  completed_at?: string;
  output_path?: string;
  subjects_count: number;
  progress_percent: number;
}

export type View = 'dashboard' | 'configure' | 'render' | 'gallery' | 'history';
