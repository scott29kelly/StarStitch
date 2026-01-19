/**
 * Render API functions
 */

import { apiClient } from './client';
import type { RenderRequest, RenderResponse, RenderListResponse } from '../types';

/**
 * Start a new render job
 */
export async function startRender(request: RenderRequest): Promise<RenderResponse> {
  return apiClient.post<RenderResponse>('/api/render', request);
}

/**
 * Get render job status
 */
export async function getRenderStatus(jobId: string): Promise<RenderResponse> {
  return apiClient.get<RenderResponse>(`/api/render/${jobId}`);
}

/**
 * Cancel a render job
 */
export async function cancelRender(jobId: string): Promise<void> {
  return apiClient.delete(`/api/render/${jobId}`);
}

/**
 * List all render jobs
 */
export async function listRenders(status?: string): Promise<RenderListResponse> {
  return apiClient.get<RenderListResponse>('/api/renders', { status });
}

/**
 * Render API namespace
 */
export const rendersApi = {
  start: startRender,
  getStatus: getRenderStatus,
  cancel: cancelRender,
  list: listRenders,
};

export default rendersApi;
