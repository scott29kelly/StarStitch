/**
 * Templates API functions
 */

import { apiClient } from './client';
import type { TemplateResponse, TemplateListResponse, CategoryResponse } from '../types';

/**
 * List all templates
 */
export async function listTemplates(
  category?: string,
  search?: string
): Promise<TemplateListResponse> {
  return apiClient.get<TemplateListResponse>('/api/templates', { category, search });
}

/**
 * Get template categories
 */
export async function getCategories(): Promise<CategoryResponse[]> {
  return apiClient.get<CategoryResponse[]>('/api/templates/categories');
}

/**
 * Get a specific template
 */
export async function getTemplate(name: string): Promise<TemplateResponse> {
  return apiClient.get<TemplateResponse>(`/api/templates/${name}`);
}

/**
 * Apply a template to a config
 */
export async function applyTemplate(
  templateName: string,
  config: Record<string, unknown> = {}
): Promise<Record<string, unknown>> {
  return apiClient.post<Record<string, unknown>>(`/api/templates/${templateName}/apply`, config);
}

/**
 * Templates API namespace
 */
export const templatesApi = {
  list: listTemplates,
  getCategories,
  get: getTemplate,
  apply: applyTemplate,
};

export default templatesApi;
