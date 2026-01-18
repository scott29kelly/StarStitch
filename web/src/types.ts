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
