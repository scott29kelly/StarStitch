/**
 * Gallery hook for fetching and managing render history
 */

import { useState, useEffect, useCallback } from 'react';
import { listRenders } from '../api/renders';
import type { RenderResponse, RenderStatusType } from '../types';

export type SortField = 'date' | 'name' | 'status';
export type SortDirection = 'asc' | 'desc';

export interface GalleryFilters {
  status?: RenderStatusType;
  search: string;
  sortField: SortField;
  sortDirection: SortDirection;
}

export interface UseGalleryResult {
  /** Render history items */
  renders: RenderResponse[];
  /** Filtered and sorted renders */
  filteredRenders: RenderResponse[];
  /** Loading state */
  isLoading: boolean;
  /** Error message */
  error: string | null;
  /** Current filters */
  filters: GalleryFilters;
  /** Update filters */
  setFilters: (filters: Partial<GalleryFilters>) => void;
  /** Refresh data from API */
  refresh: () => Promise<void>;
  /** Delete a render (local only for now) */
  deleteRender: (id: string) => void;
  /** Stats */
  stats: {
    total: number;
    complete: number;
    running: number;
    failed: number;
  };
}

const defaultFilters: GalleryFilters = {
  status: undefined,
  search: '',
  sortField: 'date',
  sortDirection: 'desc',
};

/**
 * Hook for managing gallery state with API integration
 */
export function useGallery(): UseGalleryResult {
  const [renders, setRenders] = useState<RenderResponse[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [filters, setFiltersState] = useState<GalleryFilters>(defaultFilters);

  // Fetch renders from API
  const fetchRenders = useCallback(async () => {
    try {
      setIsLoading(true);
      setError(null);
      const response = await listRenders();
      setRenders(response.renders);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load renders');
    } finally {
      setIsLoading(false);
    }
  }, []);

  // Initial fetch
  useEffect(() => {
    fetchRenders();
  }, [fetchRenders]);

  // Auto-refresh every 30 seconds if there are running renders
  useEffect(() => {
    const hasRunning = renders.some((r) => r.status === 'running' || r.status === 'pending');
    if (!hasRunning) return;

    const interval = setInterval(fetchRenders, 5000);
    return () => clearInterval(interval);
  }, [renders, fetchRenders]);

  // Update filters
  const setFilters = useCallback((newFilters: Partial<GalleryFilters>) => {
    setFiltersState((prev) => ({ ...prev, ...newFilters }));
  }, []);

  // Filter and sort renders
  const filteredRenders = renders
    .filter((render) => {
      // Status filter
      if (filters.status && render.status !== filters.status) {
        return false;
      }
      // Search filter
      if (filters.search) {
        const search = filters.search.toLowerCase();
        return (
          render.project_name.toLowerCase().includes(search) ||
          render.id.toLowerCase().includes(search)
        );
      }
      return true;
    })
    .sort((a, b) => {
      const direction = filters.sortDirection === 'asc' ? 1 : -1;

      switch (filters.sortField) {
        case 'date':
          return direction * (new Date(b.created_at).getTime() - new Date(a.created_at).getTime());
        case 'name':
          return direction * a.project_name.localeCompare(b.project_name);
        case 'status':
          return direction * a.status.localeCompare(b.status);
        default:
          return 0;
      }
    });

  // Delete render (local state only - API would need DELETE endpoint for job cleanup)
  const deleteRender = useCallback((id: string) => {
    setRenders((prev) => prev.filter((r) => r.id !== id));
  }, []);

  // Calculate stats
  const stats = {
    total: renders.length,
    complete: renders.filter((r) => r.status === 'complete').length,
    running: renders.filter((r) => r.status === 'running' || r.status === 'pending').length,
    failed: renders.filter((r) => r.status === 'error' || r.status === 'cancelled').length,
  };

  return {
    renders,
    filteredRenders,
    isLoading,
    error,
    filters,
    setFilters,
    refresh: fetchRenders,
    deleteRender,
    stats,
  };
}

export default useGallery;
