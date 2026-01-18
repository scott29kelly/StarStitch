/**
 * RenderHistory Component
 * Displays a list of past and current render jobs with status indicators.
 */

import { motion } from 'framer-motion';
import { 
  RefreshCw, 
  Trash2, 
  Download, 
  Clock, 
  CheckCircle, 
  XCircle, 
  AlertCircle,
  Loader2,
  ExternalLink,
} from 'lucide-react';
import type { RenderJob, JobState } from '../types';

interface RenderHistoryProps {
  jobs: RenderJob[];
  isLoading?: boolean;
  onRefresh?: () => void;
  onDelete?: (jobId: string) => void;
  onDownload?: (jobId: string, outputPath: string) => void;
  onViewDetails?: (jobId: string) => void;
  hasMore?: boolean;
  onLoadMore?: () => void;
}

/**
 * Get status icon and color for a job state
 */
function getStatusDisplay(state: JobState): { icon: React.ReactNode; color: string; label: string } {
  switch (state) {
    case 'pending':
      return {
        icon: <Clock className="w-4 h-4" />,
        color: 'text-zinc-400',
        label: 'Pending',
      };
    case 'running':
      return {
        icon: <Loader2 className="w-4 h-4 animate-spin" />,
        color: 'text-violet-400',
        label: 'Running',
      };
    case 'complete':
      return {
        icon: <CheckCircle className="w-4 h-4" />,
        color: 'text-emerald-400',
        label: 'Complete',
      };
    case 'failed':
      return {
        icon: <XCircle className="w-4 h-4" />,
        color: 'text-red-400',
        label: 'Failed',
      };
    case 'cancelled':
      return {
        icon: <AlertCircle className="w-4 h-4" />,
        color: 'text-amber-400',
        label: 'Cancelled',
      };
    default:
      return {
        icon: <Clock className="w-4 h-4" />,
        color: 'text-zinc-400',
        label: 'Unknown',
      };
  }
}

/**
 * Format a date string for display
 */
function formatDate(dateString: string): string {
  const date = new Date(dateString);
  const now = new Date();
  const diff = now.getTime() - date.getTime();
  
  // Less than a minute
  if (diff < 60000) {
    return 'Just now';
  }
  
  // Less than an hour
  if (diff < 3600000) {
    const minutes = Math.floor(diff / 60000);
    return `${minutes}m ago`;
  }
  
  // Less than a day
  if (diff < 86400000) {
    const hours = Math.floor(diff / 3600000);
    return `${hours}h ago`;
  }
  
  // Format as date
  return date.toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric',
    hour: 'numeric',
    minute: '2-digit',
  });
}

export function RenderHistory({
  jobs,
  isLoading = false,
  onRefresh,
  onDelete,
  onDownload,
  onViewDetails,
  hasMore = false,
  onLoadMore,
}: RenderHistoryProps) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -20 }}
      className="p-6 max-w-4xl mx-auto"
    >
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-semibold text-white">Render History</h1>
          <p className="text-zinc-400 text-sm mt-1">
            View and manage your render jobs
          </p>
        </div>
        
        {onRefresh && (
          <button
            onClick={onRefresh}
            disabled={isLoading}
            className="flex items-center gap-2 px-4 py-2 bg-zinc-800 hover:bg-zinc-700 
                       text-zinc-300 rounded-lg transition-colors disabled:opacity-50"
          >
            <RefreshCw className={`w-4 h-4 ${isLoading ? 'animate-spin' : ''}`} />
            Refresh
          </button>
        )}
      </div>

      {/* Job List */}
      <div className="space-y-3">
        {jobs.length === 0 && !isLoading ? (
          <div className="text-center py-12 bg-zinc-900/50 rounded-xl border border-zinc-800">
            <Clock className="w-12 h-12 text-zinc-600 mx-auto mb-4" />
            <p className="text-zinc-400">No render jobs yet</p>
            <p className="text-zinc-500 text-sm mt-1">
              Start a new render to see it here
            </p>
          </div>
        ) : (
          jobs.map((job) => {
            const status = getStatusDisplay(job.state);
            
            return (
              <motion.div
                key={job.job_id}
                layout
                initial={{ opacity: 0, scale: 0.95 }}
                animate={{ opacity: 1, scale: 1 }}
                className="bg-zinc-900/50 rounded-xl border border-zinc-800 p-4 
                           hover:border-zinc-700 transition-colors"
              >
                <div className="flex items-center justify-between">
                  {/* Left: Job info */}
                  <div className="flex items-center gap-4">
                    {/* Status icon */}
                    <div className={`${status.color}`}>
                      {status.icon}
                    </div>
                    
                    {/* Job details */}
                    <div>
                      <h3 className="text-white font-medium">
                        {job.project_name}
                      </h3>
                      <div className="flex items-center gap-3 text-sm text-zinc-500 mt-1">
                        <span className={status.color}>{status.label}</span>
                        <span>•</span>
                        <span>{job.subjects_count} subjects</span>
                        <span>•</span>
                        <span>{formatDate(job.created_at)}</span>
                      </div>
                    </div>
                  </div>

                  {/* Right: Progress / Actions */}
                  <div className="flex items-center gap-3">
                    {/* Progress bar for running jobs */}
                    {job.state === 'running' && (
                      <div className="w-32">
                        <div className="flex items-center justify-between text-xs text-zinc-400 mb-1">
                          <span>Progress</span>
                          <span>{Math.round(job.progress_percent)}%</span>
                        </div>
                        <div className="h-1.5 bg-zinc-800 rounded-full overflow-hidden">
                          <div 
                            className="h-full bg-violet-500 rounded-full transition-all duration-300"
                            style={{ width: `${job.progress_percent}%` }}
                          />
                        </div>
                      </div>
                    )}

                    {/* Action buttons */}
                    <div className="flex items-center gap-2">
                      {/* View details */}
                      {onViewDetails && (
                        <button
                          onClick={() => onViewDetails(job.job_id)}
                          className="p-2 text-zinc-400 hover:text-white hover:bg-zinc-800 
                                     rounded-lg transition-colors"
                          title="View details"
                        >
                          <ExternalLink className="w-4 h-4" />
                        </button>
                      )}

                      {/* Download (only for complete jobs) */}
                      {job.state === 'complete' && job.output_path && onDownload && (
                        <button
                          onClick={() => onDownload(job.job_id, job.output_path!)}
                          className="p-2 text-zinc-400 hover:text-emerald-400 hover:bg-zinc-800 
                                     rounded-lg transition-colors"
                          title="Download"
                        >
                          <Download className="w-4 h-4" />
                        </button>
                      )}

                      {/* Delete (not for running jobs) */}
                      {job.state !== 'running' && onDelete && (
                        <button
                          onClick={() => onDelete(job.job_id)}
                          className="p-2 text-zinc-400 hover:text-red-400 hover:bg-zinc-800 
                                     rounded-lg transition-colors"
                          title="Delete"
                        >
                          <Trash2 className="w-4 h-4" />
                        </button>
                      )}
                    </div>
                  </div>
                </div>
              </motion.div>
            );
          })
        )}

        {/* Loading state */}
        {isLoading && (
          <div className="flex items-center justify-center py-8">
            <Loader2 className="w-6 h-6 text-violet-400 animate-spin" />
          </div>
        )}

        {/* Load more button */}
        {hasMore && onLoadMore && !isLoading && (
          <button
            onClick={onLoadMore}
            className="w-full py-3 text-zinc-400 hover:text-white 
                       bg-zinc-900/50 hover:bg-zinc-800/50 
                       border border-zinc-800 rounded-xl transition-colors"
          >
            Load more
          </button>
        )}
      </div>
    </motion.div>
  );
}
