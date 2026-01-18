/**
 * StarStitch API Client
 * REST API client for the FastAPI backend.
 */

// API base URL - defaults to localhost:8000 for development
const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

/**
 * API error response
 */
export interface ApiError {
  error: string;
  message: string;
  details?: Record<string, unknown>;
}

/**
 * Subject in the render sequence
 */
export interface SubjectSchema {
  id: string;
  name: string;
  visual_prompt: string;
}

/**
 * Render settings
 */
export interface SettingsSchema {
  aspect_ratio: string;
  transition_duration_sec: number;
  image_model: string;
  video_model: string;
  variants: string[];
}

/**
 * Global scene settings
 */
export interface GlobalSceneSchema {
  location_prompt: string;
  negative_prompt: string;
}

/**
 * Audio configuration
 */
export interface AudioSchema {
  enabled: boolean;
  audio_path: string;
  volume: number;
  fade_in_sec: number;
  fade_out_sec: number;
  loop: boolean;
  normalize: boolean;
}

/**
 * Render request body
 */
export interface RenderRequest {
  project_name: string;
  output_folder?: string;
  settings?: Partial<SettingsSchema>;
  global_scene: GlobalSceneSchema;
  sequence: SubjectSchema[];
  audio?: AudioSchema;
  template_name?: string;
}

/**
 * Render progress update
 */
export interface RenderProgress {
  step: number;
  total_steps: number;
  phase: string;
  message: string;
  progress_percent: number;
  current_subject?: string;
  elapsed_seconds: number;
  estimated_remaining_seconds?: number;
}

/**
 * Job state enum
 */
export type JobState = 'pending' | 'running' | 'complete' | 'failed' | 'cancelled';

/**
 * Render status response
 */
export interface RenderStatus {
  job_id: string;
  state: JobState;
  progress?: RenderProgress;
  config: Record<string, unknown>;
  created_at: string;
  started_at?: string;
  completed_at?: string;
  output_path?: string;
  variant_paths: Record<string, string>;
  error_message?: string;
  render_dir?: string;
}

/**
 * Response after starting a render
 */
export interface RenderResponse {
  job_id: string;
  message: string;
  state: JobState;
  websocket_url: string;
}

/**
 * Render list item
 */
export interface RenderListItem {
  job_id: string;
  project_name: string;
  state: JobState;
  created_at: string;
  completed_at?: string;
  output_path?: string;
  subjects_count: number;
  progress_percent: number;
}

/**
 * Render list response
 */
export interface RenderListResponse {
  renders: RenderListItem[];
  total: number;
  page: number;
  page_size: number;
  has_more: boolean;
}

/**
 * Template info
 */
export interface TemplateInfo {
  name: string;
  display_name: string;
  description: string;
  category: string;
  tags: string[];
  thumbnail?: string;
  author: string;
  version: string;
}

/**
 * Template list response
 */
export interface TemplateListResponse {
  templates: TemplateInfo[];
  categories: Array<{ name: string; count: number }>;
  total: number;
}

/**
 * Template detail response
 */
export interface TemplateDetailResponse {
  info: TemplateInfo;
  base_config: Record<string, unknown>;
}

/**
 * Health check response
 */
export interface HealthResponse {
  status: string;
  version: string;
  queue: {
    max_concurrent: number;
    pending_jobs: number;
    running_jobs: number;
    total_jobs: number;
  };
}

/**
 * API client class for making REST calls
 */
class ApiClient {
  private baseUrl: string;

  constructor(baseUrl: string = API_BASE_URL) {
    this.baseUrl = baseUrl;
  }

  /**
   * Make a fetch request with error handling
   */
  private async request<T>(
    path: string,
    options: RequestInit = {}
  ): Promise<T> {
    const url = `${this.baseUrl}${path}`;
    
    const headers: HeadersInit = {
      'Content-Type': 'application/json',
      ...options.headers,
    };

    const response = await fetch(url, {
      ...options,
      headers,
    });

    if (!response.ok) {
      let error: ApiError;
      try {
        error = await response.json();
      } catch {
        error = {
          error: 'request_failed',
          message: `Request failed with status ${response.status}`,
        };
      }
      throw new Error(error.message || error.error);
    }

    return response.json();
  }

  // ===== Render Endpoints =====

  /**
   * Start a new render job
   */
  async startRender(request: RenderRequest): Promise<RenderResponse> {
    return this.request<RenderResponse>('/api/render', {
      method: 'POST',
      body: JSON.stringify(request),
    });
  }

  /**
   * Get render job status
   */
  async getRenderStatus(jobId: string): Promise<RenderStatus> {
    return this.request<RenderStatus>(`/api/render/${jobId}`);
  }

  /**
   * Cancel a render job
   */
  async cancelRender(jobId: string): Promise<{ job_id: string; message: string; state: string }> {
    return this.request(`/api/render/${jobId}`, {
      method: 'DELETE',
    });
  }

  /**
   * List all renders with pagination
   */
  async listRenders(
    page: number = 1,
    pageSize: number = 20,
    state?: JobState
  ): Promise<RenderListResponse> {
    const params = new URLSearchParams({
      page: String(page),
      page_size: String(pageSize),
    });
    if (state) {
      params.append('state', state);
    }
    return this.request<RenderListResponse>(`/api/renders?${params}`);
  }

  /**
   * Delete a render from history
   */
  async deleteRender(jobId: string): Promise<{ job_id: string; message: string }> {
    return this.request(`/api/renders/${jobId}`, {
      method: 'DELETE',
    });
  }

  // ===== Template Endpoints =====

  /**
   * List available templates
   */
  async listTemplates(category?: string, search?: string): Promise<TemplateListResponse> {
    const params = new URLSearchParams();
    if (category) {
      params.append('category', category);
    }
    if (search) {
      params.append('search', search);
    }
    const query = params.toString();
    return this.request<TemplateListResponse>(`/api/templates${query ? `?${query}` : ''}`);
  }

  /**
   * Get template details
   */
  async getTemplate(name: string): Promise<TemplateDetailResponse> {
    return this.request<TemplateDetailResponse>(`/api/templates/${name}`);
  }

  // ===== System Endpoints =====

  /**
   * Health check
   */
  async healthCheck(): Promise<HealthResponse> {
    return this.request<HealthResponse>('/health');
  }

  /**
   * Get WebSocket URL for a job
   */
  getWebSocketUrl(jobId: string): string {
    const wsBase = this.baseUrl.replace(/^http/, 'ws');
    return `${wsBase}/ws/render/${jobId}`;
  }
}

// Export singleton instance
export const api = new ApiClient();

// Export class for custom instances
export { ApiClient };
