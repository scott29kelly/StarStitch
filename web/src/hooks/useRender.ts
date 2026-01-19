/**
 * Render hook for managing render job state
 */

import { useState, useCallback, useEffect } from 'react';
import { rendersApi } from '../api/renders';
import { useWebSocket, type WebSocketStatus } from './useWebSocket';
import type {
  RenderRequest,
  RenderResponse,
  RenderProgress,
  ProgressEvent,
  ProjectConfig
} from '../types';

export type RenderState = 'idle' | 'starting' | 'rendering' | 'complete' | 'error' | 'cancelled';

export interface UseRenderResult {
  /** Current render state */
  state: RenderState;
  /** Current job ID */
  jobId: string | null;
  /** Render progress information */
  progress: RenderProgress;
  /** Last error message */
  error: string | null;
  /** WebSocket connection status */
  wsStatus: WebSocketStatus;
  /** Start a new render */
  startRender: (config: ProjectConfig) => Promise<void>;
  /** Cancel the current render */
  cancelRender: () => Promise<void>;
  /** Reset the render state */
  reset: () => void;
  /** All progress events */
  events: ProgressEvent[];
}

/**
 * Convert ProjectConfig to RenderRequest
 */
function configToRequest(config: ProjectConfig): RenderRequest {
  return {
    project_name: config.project_name,
    output_folder: config.output_folder,
    settings: {
      aspect_ratio: config.settings.aspect_ratio,
      transition_duration_sec: config.settings.transition_duration_sec,
      image_model: config.settings.image_model,
      video_model: config.settings.video_model,
      variants: [],
    },
    global_scene: {
      location_prompt: config.global_scene.location_prompt,
      negative_prompt: config.global_scene.negative_prompt,
    },
    audio: {
      enabled: false,
      audio_path: '',
      volume: 0.8,
      fade_in_sec: 1.0,
      fade_out_sec: 2.0,
      loop: true,
      normalize: true,
    },
    sequence: config.sequence.map((s) => ({
      id: s.id,
      name: s.name,
      visual_prompt: s.visual_prompt,
    })),
  };
}

/**
 * Hook for managing render job state with WebSocket progress
 */
export function useRender(): UseRenderResult {
  const [state, setState] = useState<RenderState>('idle');
  const [jobId, setJobId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [progress, setProgress] = useState<RenderProgress>({
    status: 'idle',
    current_step: 0,
    total_steps: 0,
    progress_percent: 0,
    message: '',
    elapsed_time: 0,
  });

  // WebSocket connection for real-time progress
  const {
    status: wsStatus,
    events,
    cancelJob: wsCancelJob,
  } = useWebSocket(jobId, {
    onEvent: (event) => {
      // Update progress from WebSocket event
      setProgress((prev) => ({
        ...prev,
        current_step: event.current_step ?? prev.current_step,
        total_steps: event.total_steps ?? prev.total_steps,
        progress_percent: event.progress_percent ?? prev.progress_percent,
        current_subject: event.subject ?? prev.current_subject,
        message: event.message || prev.message,
      }));

      // Update state based on event type
      switch (event.type) {
        case 'job_started':
          setState('rendering');
          setProgress((prev) => ({
            ...prev,
            status: 'rendering',
          }));
          break;

        case 'job_completed':
          setState('complete');
          setProgress((prev) => ({
            ...prev,
            status: 'complete',
            progress_percent: 100,
            elapsed_time: event.data?.elapsed_seconds ?? prev.elapsed_time,
          }));
          break;

        case 'job_failed':
          setState('error');
          setError(event.data?.error ?? event.message);
          setProgress((prev) => ({
            ...prev,
            status: 'error',
          }));
          break;

        case 'job_cancelled':
          setState('cancelled');
          setProgress((prev) => ({
            ...prev,
            status: 'idle',
          }));
          break;

        case 'progress':
        case 'step_progress':
          setProgress((prev) => ({
            ...prev,
            status: 'rendering',
          }));
          break;
      }
    },
  });

  /**
   * Start a new render job
   */
  const startRender = useCallback(async (config: ProjectConfig) => {
    try {
      // Reset state
      setState('starting');
      setError(null);
      setProgress({
        status: 'preparing',
        current_step: 0,
        total_steps: 0,
        progress_percent: 0,
        message: 'Starting render...',
        elapsed_time: 0,
      });

      // Convert config to request
      const request = configToRequest(config);

      // Start the render job
      const response = await rendersApi.start(request);

      // Set job ID to trigger WebSocket connection
      setJobId(response.id);

      // Update progress from initial response
      setProgress({
        status: 'preparing',
        current_step: response.current_step,
        total_steps: response.total_steps,
        progress_percent: response.progress_percent,
        message: response.message,
        elapsed_time: response.elapsed_seconds,
      });
    } catch (err) {
      setState('error');
      setError(err instanceof Error ? err.message : 'Failed to start render');
      setProgress((prev) => ({
        ...prev,
        status: 'error',
      }));
    }
  }, []);

  /**
   * Cancel the current render job
   */
  const cancelRender = useCallback(async () => {
    if (!jobId) return;

    try {
      // Try WebSocket cancel first (faster)
      wsCancelJob();

      // Also send HTTP cancel request
      await rendersApi.cancel(jobId);

      setState('cancelled');
      setProgress((prev) => ({
        ...prev,
        status: 'idle',
        message: 'Render cancelled',
      }));
    } catch (err) {
      console.error('Failed to cancel render:', err);
    }
  }, [jobId, wsCancelJob]);

  /**
   * Reset the render state
   */
  const reset = useCallback(() => {
    setState('idle');
    setJobId(null);
    setError(null);
    setProgress({
      status: 'idle',
      current_step: 0,
      total_steps: 0,
      progress_percent: 0,
      message: '',
      elapsed_time: 0,
    });
  }, []);

  return {
    state,
    jobId,
    progress,
    error,
    wsStatus,
    startRender,
    cancelRender,
    reset,
    events,
  };
}

export default useRender;
