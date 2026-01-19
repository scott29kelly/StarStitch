import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Film,
  Download,
  Trash2,
  Calendar,
  Clock,
  Play,
  Search,
  Filter,
  RefreshCw,
  CheckCircle2,
  XCircle,
  Loader2,
  SlidersHorizontal,
  ChevronDown,
  Sparkles,
  TrendingUp,
  AlertCircle,
  ExternalLink,
  MoreHorizontal,
} from 'lucide-react';
import { useGallery, type SortField } from '../hooks/useGallery';
import type { RenderResponse, RenderStatusType } from '../types';

// ============================================================================
// ANIMATION VARIANTS
// ============================================================================

const containerVariants = {
  hidden: { opacity: 0 },
  visible: {
    opacity: 1,
    transition: { staggerChildren: 0.06, delayChildren: 0.1 },
  },
};

const itemVariants = {
  hidden: { opacity: 0, y: 24, scale: 0.96 },
  visible: {
    opacity: 1,
    y: 0,
    scale: 1,
    transition: { type: 'spring', stiffness: 300, damping: 24 },
  },
  exit: {
    opacity: 0,
    scale: 0.96,
    transition: { duration: 0.2 },
  },
};

const fadeInUp = {
  hidden: { opacity: 0, y: 20 },
  visible: { opacity: 1, y: 0, transition: { duration: 0.5, ease: [0.16, 1, 0.3, 1] } },
};

// ============================================================================
// HELPER FUNCTIONS
// ============================================================================

function formatDate(dateString: string): string {
  const date = new Date(dateString);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffMins = Math.floor(diffMs / 60000);
  const diffHours = Math.floor(diffMs / 3600000);
  const diffDays = Math.floor(diffMs / 86400000);

  if (diffMins < 1) return 'Just now';
  if (diffMins < 60) return `${diffMins}m ago`;
  if (diffHours < 24) return `${diffHours}h ago`;
  if (diffDays < 7) return `${diffDays}d ago`;

  return date.toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric',
    year: date.getFullYear() !== now.getFullYear() ? 'numeric' : undefined,
  });
}

function formatDuration(seconds: number): string {
  if (seconds < 60) return `0:${Math.round(seconds).toString().padStart(2, '0')}`;
  const mins = Math.floor(seconds / 60);
  const secs = Math.round(seconds % 60);
  return `${mins}:${secs.toString().padStart(2, '0')}`;
}

function getStatusConfig(status: RenderStatusType) {
  switch (status) {
    case 'complete':
      return {
        label: 'Complete',
        icon: CheckCircle2,
        color: 'text-emerald-400',
        bg: 'bg-emerald-500/10',
        border: 'border-emerald-500/20',
        glow: 'shadow-emerald-500/20',
      };
    case 'running':
      return {
        label: 'Rendering',
        icon: Loader2,
        color: 'text-violet-400',
        bg: 'bg-violet-500/10',
        border: 'border-violet-500/20',
        glow: 'shadow-violet-500/20',
        animate: true,
      };
    case 'pending':
      return {
        label: 'Queued',
        icon: Clock,
        color: 'text-amber-400',
        bg: 'bg-amber-500/10',
        border: 'border-amber-500/20',
        glow: 'shadow-amber-500/20',
      };
    case 'error':
      return {
        label: 'Failed',
        icon: XCircle,
        color: 'text-red-400',
        bg: 'bg-red-500/10',
        border: 'border-red-500/20',
        glow: 'shadow-red-500/20',
      };
    case 'cancelled':
      return {
        label: 'Cancelled',
        icon: AlertCircle,
        color: 'text-zinc-400',
        bg: 'bg-zinc-500/10',
        border: 'border-zinc-500/20',
        glow: 'shadow-zinc-500/20',
      };
    default:
      return {
        label: status,
        icon: Film,
        color: 'text-zinc-400',
        bg: 'bg-zinc-500/10',
        border: 'border-zinc-500/20',
        glow: 'shadow-zinc-500/20',
      };
  }
}

// ============================================================================
// SUB-COMPONENTS
// ============================================================================

function StatusBadge({ status }: { status: RenderStatusType }) {
  const config = getStatusConfig(status);
  const Icon = config.icon;

  return (
    <span
      className={`
        inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium
        ${config.bg} ${config.color} border ${config.border}
        transition-all duration-300
      `}
    >
      <Icon
        size={12}
        className={config.animate ? 'animate-spin' : ''}
      />
      {config.label}
    </span>
  );
}

function StatCard({
  icon: Icon,
  label,
  value,
  trend,
  color,
}: {
  icon: React.ElementType;
  label: string;
  value: number;
  trend?: string;
  color: string;
}) {
  return (
    <motion.div
      variants={fadeInUp}
      className="glass-card p-4 flex items-center gap-4"
    >
      <div className={`w-12 h-12 rounded-xl ${color} flex items-center justify-center`}>
        <Icon size={22} className="text-white" />
      </div>
      <div className="flex-1">
        <p className="text-2xl font-bold text-snow">{value}</p>
        <p className="text-sm text-silver">{label}</p>
      </div>
      {trend && (
        <span className="text-xs text-emerald-400 flex items-center gap-1">
          <TrendingUp size={12} />
          {trend}
        </span>
      )}
    </motion.div>
  );
}

function SkeletonCard() {
  return (
    <div className="glass-card overflow-hidden">
      <div className="aspect-video bg-smoke shimmer" />
      <div className="p-5 space-y-3">
        <div className="h-5 bg-smoke rounded-lg w-3/4 shimmer" />
        <div className="h-4 bg-smoke rounded-lg w-1/2 shimmer" />
        <div className="flex gap-2 pt-2">
          <div className="h-8 bg-smoke rounded-lg flex-1 shimmer" />
          <div className="h-8 w-8 bg-smoke rounded-lg shimmer" />
        </div>
      </div>
    </div>
  );
}

function RenderCard({
  render,
  onPlay,
  onDownload,
  onDelete,
}: {
  render: RenderResponse;
  onPlay: () => void;
  onDownload: () => void;
  onDelete: () => void;
}) {
  const [showMenu, setShowMenu] = useState(false);
  const statusConfig = getStatusConfig(render.status);
  const isComplete = render.status === 'complete';
  const isRunning = render.status === 'running' || render.status === 'pending';

  return (
    <motion.div
      variants={itemVariants}
      layout
      className="glass-card-hover group cursor-pointer overflow-hidden relative"
      onClick={isComplete ? onPlay : undefined}
    >
      {/* Animated gradient border for running renders */}
      {isRunning && (
        <div className="absolute inset-0 rounded-xl gradient-border-animated opacity-50" />
      )}

      {/* Thumbnail Area */}
      <div className="relative aspect-video bg-gradient-to-br from-smoke to-obsidian overflow-hidden">
        {/* Animated background for running */}
        {isRunning && (
          <div className="absolute inset-0 bg-gradient-to-r from-violet-500/10 via-fuchsia-500/10 to-violet-500/10 animate-pulse" />
        )}

        {/* Placeholder content */}
        <div className="absolute inset-0 flex items-center justify-center">
          <motion.div
            className={`
              w-20 h-20 rounded-2xl flex items-center justify-center
              ${isRunning ? 'bg-violet-500/20' : isComplete ? 'bg-emerald-500/10' : 'bg-smoke/50'}
            `}
            animate={isRunning ? { scale: [1, 1.05, 1] } : {}}
            transition={{ duration: 2, repeat: Infinity }}
          >
            {isRunning ? (
              <Loader2 size={32} className="text-violet-400 animate-spin" />
            ) : (
              <Film size={32} className={isComplete ? 'text-emerald-400' : 'text-mist'} />
            )}
          </motion.div>
        </div>

        {/* Play Overlay */}
        {isComplete && (
          <div className="absolute inset-0 bg-obsidian/70 opacity-0 group-hover:opacity-100 transition-all duration-300 flex items-center justify-center backdrop-blur-sm">
            <motion.div
              className="w-16 h-16 rounded-full bg-white/10 backdrop-blur-md flex items-center justify-center border border-white/20"
              whileHover={{ scale: 1.1 }}
              whileTap={{ scale: 0.95 }}
            >
              <Play size={28} className="text-white ml-1" fill="white" />
            </motion.div>
          </div>
        )}

        {/* Progress bar for running renders */}
        {isRunning && render.progress_percent > 0 && (
          <div className="absolute bottom-0 left-0 right-0 h-1 bg-obsidian/50">
            <motion.div
              className="h-full bg-gradient-to-r from-violet-500 to-fuchsia-500"
              initial={{ width: 0 }}
              animate={{ width: `${render.progress_percent}%` }}
              transition={{ duration: 0.5 }}
            />
          </div>
        )}

        {/* Duration Badge */}
        {isComplete && render.elapsed_seconds > 0 && (
          <div className="absolute bottom-3 right-3 bg-obsidian/90 backdrop-blur-sm px-2.5 py-1 rounded-lg text-xs text-cloud font-mono border border-white/10">
            {formatDuration(render.elapsed_seconds)}
          </div>
        )}

        {/* Status Badge */}
        <div className="absolute top-3 left-3">
          <StatusBadge status={render.status} />
        </div>

        {/* Menu Button */}
        <div className="absolute top-3 right-3">
          <button
            onClick={(e) => {
              e.stopPropagation();
              setShowMenu(!showMenu);
            }}
            className="w-8 h-8 rounded-lg bg-obsidian/80 backdrop-blur-sm flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity border border-white/10 hover:bg-smoke"
          >
            <MoreHorizontal size={16} className="text-cloud" />
          </button>

          {/* Dropdown Menu */}
          <AnimatePresence>
            {showMenu && (
              <motion.div
                initial={{ opacity: 0, y: -8, scale: 0.95 }}
                animate={{ opacity: 1, y: 0, scale: 1 }}
                exit={{ opacity: 0, y: -8, scale: 0.95 }}
                className="absolute top-full right-0 mt-2 w-40 bg-slate/95 backdrop-blur-xl rounded-lg border border-white/10 shadow-xl overflow-hidden z-10"
                onClick={(e) => e.stopPropagation()}
              >
                {isComplete && (
                  <button
                    onClick={onDownload}
                    className="w-full px-4 py-2.5 text-left text-sm text-cloud hover:bg-white/5 flex items-center gap-2 transition-colors"
                  >
                    <Download size={14} />
                    Download
                  </button>
                )}
                {render.output_path && (
                  <button
                    onClick={() => window.open(render.output_path!, '_blank')}
                    className="w-full px-4 py-2.5 text-left text-sm text-cloud hover:bg-white/5 flex items-center gap-2 transition-colors"
                  >
                    <ExternalLink size={14} />
                    Open File
                  </button>
                )}
                <button
                  onClick={onDelete}
                  className="w-full px-4 py-2.5 text-left text-sm text-red-400 hover:bg-red-500/10 flex items-center gap-2 transition-colors"
                >
                  <Trash2 size={14} />
                  Delete
                </button>
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      </div>

      {/* Content */}
      <div className="p-5">
        <h3 className="font-semibold text-snow text-lg mb-1 group-hover:text-aurora transition-colors truncate">
          {render.project_name}
        </h3>

        <p className="text-sm text-mist mb-3 line-clamp-1">
          {render.message || 'No status message'}
        </p>

        <div className="flex items-center gap-4 text-xs text-silver">
          <span className="flex items-center gap-1.5">
            <Calendar size={12} />
            {formatDate(render.created_at)}
          </span>
          {render.total_steps > 0 && (
            <span className="flex items-center gap-1.5">
              <Sparkles size={12} />
              {render.current_step}/{render.total_steps} steps
            </span>
          )}
        </div>

        {/* Action Buttons */}
        {isComplete && (
          <div className="flex items-center gap-2 pt-4 mt-4 border-t border-smoke">
            <button
              onClick={(e) => {
                e.stopPropagation();
                onDownload();
              }}
              className="flex-1 flex items-center justify-center gap-2 py-2.5 rounded-lg bg-gradient-to-r from-violet-600 to-fuchsia-600 hover:from-violet-500 hover:to-fuchsia-500 text-white font-medium transition-all hover:shadow-lg hover:shadow-violet-500/25"
            >
              <Download size={16} />
              <span className="text-sm">Download</span>
            </button>
            <button
              onClick={(e) => {
                e.stopPropagation();
                onDelete();
              }}
              className="p-2.5 rounded-lg bg-smoke/50 hover:bg-red-500/20 text-mist hover:text-red-400 transition-all"
            >
              <Trash2 size={16} />
            </button>
          </div>
        )}
      </div>
    </motion.div>
  );
}

function EmptyState({ hasFilters, onClear }: { hasFilters: boolean; onClear: () => void }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className="col-span-full"
    >
      <div className="glass-card p-16 text-center max-w-lg mx-auto">
        <motion.div
          className="w-24 h-24 rounded-2xl bg-gradient-to-br from-violet-500/20 to-fuchsia-500/20 flex items-center justify-center mx-auto mb-6"
          animate={{ scale: [1, 1.05, 1], rotate: [0, 5, -5, 0] }}
          transition={{ duration: 4, repeat: Infinity }}
        >
          <Film size={40} className="text-violet-400" />
        </motion.div>

        {hasFilters ? (
          <>
            <h2 className="text-2xl font-bold text-snow mb-2">No Matches Found</h2>
            <p className="text-silver mb-6">
              No renders match your current filters. Try adjusting your search or filters.
            </p>
            <button
              onClick={onClear}
              className="btn-ghost"
            >
              Clear Filters
            </button>
          </>
        ) : (
          <>
            <h2 className="text-2xl font-bold text-snow mb-2">No Renders Yet</h2>
            <p className="text-silver max-w-md mx-auto">
              Your completed stitches will appear here. Start by creating a new project
              and let the AI work its magic.
            </p>
          </>
        )}
      </div>
    </motion.div>
  );
}

// ============================================================================
// MAIN GALLERY COMPONENT
// ============================================================================

export function Gallery() {
  const {
    filteredRenders,
    isLoading,
    error,
    filters,
    setFilters,
    refresh,
    deleteRender,
    stats,
  } = useGallery();

  const [showFilters, setShowFilters] = useState(false);

  const statusOptions: { value: RenderStatusType | ''; label: string }[] = [
    { value: '', label: 'All Status' },
    { value: 'complete', label: 'Complete' },
    { value: 'running', label: 'Running' },
    { value: 'pending', label: 'Pending' },
    { value: 'error', label: 'Failed' },
    { value: 'cancelled', label: 'Cancelled' },
  ];

  const sortOptions: { value: SortField; label: string }[] = [
    { value: 'date', label: 'Date' },
    { value: 'name', label: 'Name' },
    { value: 'status', label: 'Status' },
  ];

  const hasActiveFilters = filters.status || filters.search;

  const handlePlay = (render: RenderResponse) => {
    if (render.output_path) {
      window.open(render.output_path, '_blank');
    }
  };

  const handleDownload = (render: RenderResponse) => {
    if (render.output_path) {
      const link = document.createElement('a');
      link.href = render.output_path;
      link.download = `${render.project_name}.mp4`;
      link.click();
    }
  };

  const handleDelete = (render: RenderResponse) => {
    if (confirm(`Delete "${render.project_name}"? This cannot be undone.`)) {
      deleteRender(render.id);
    }
  };

  const clearFilters = () => {
    setFilters({ status: undefined, search: '' });
  };

  return (
    <div className="max-w-7xl mx-auto space-y-8">
      {/* Header */}
      <motion.div
        initial={{ opacity: 0, y: -20 }}
        animate={{ opacity: 1, y: 0 }}
        className="flex flex-col md:flex-row md:items-end justify-between gap-4"
      >
        <div>
          <h1 className="text-4xl font-bold text-snow mb-2 tracking-tight">
            Your Gallery
          </h1>
          <p className="text-silver">
            {stats.total} render{stats.total !== 1 ? 's' : ''} in your library
          </p>
        </div>

        <button
          onClick={refresh}
          disabled={isLoading}
          className="btn-ghost flex items-center gap-2 self-start md:self-auto"
        >
          <RefreshCw size={16} className={isLoading ? 'animate-spin' : ''} />
          Refresh
        </button>
      </motion.div>

      {/* Stats Cards */}
      <motion.div
        variants={containerVariants}
        initial="hidden"
        animate="visible"
        className="grid grid-cols-2 md:grid-cols-4 gap-4"
      >
        <StatCard
          icon={Film}
          label="Total Renders"
          value={stats.total}
          color="bg-gradient-to-br from-violet-600 to-fuchsia-600"
        />
        <StatCard
          icon={CheckCircle2}
          label="Complete"
          value={stats.complete}
          color="bg-gradient-to-br from-emerald-600 to-teal-600"
        />
        <StatCard
          icon={Loader2}
          label="In Progress"
          value={stats.running}
          color="bg-gradient-to-br from-amber-600 to-orange-600"
        />
        <StatCard
          icon={XCircle}
          label="Failed"
          value={stats.failed}
          color="bg-gradient-to-br from-red-600 to-pink-600"
        />
      </motion.div>

      {/* Search & Filters Bar */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.2 }}
        className="glass-card p-4"
      >
        <div className="flex flex-col md:flex-row gap-4">
          {/* Search Input */}
          <div className="relative flex-1">
            <Search size={18} className="absolute left-4 top-1/2 -translate-y-1/2 text-mist" />
            <input
              type="text"
              placeholder="Search renders..."
              value={filters.search}
              onChange={(e) => setFilters({ search: e.target.value })}
              className="input-field pl-12 w-full"
            />
          </div>

          {/* Filter Toggle */}
          <button
            onClick={() => setShowFilters(!showFilters)}
            className={`btn-ghost flex items-center gap-2 ${showFilters ? 'bg-smoke' : ''}`}
          >
            <SlidersHorizontal size={16} />
            Filters
            {hasActiveFilters && (
              <span className="w-2 h-2 rounded-full bg-violet-500" />
            )}
            <ChevronDown
              size={14}
              className={`transition-transform ${showFilters ? 'rotate-180' : ''}`}
            />
          </button>
        </div>

        {/* Expanded Filters */}
        <AnimatePresence>
          {showFilters && (
            <motion.div
              initial={{ height: 0, opacity: 0 }}
              animate={{ height: 'auto', opacity: 1 }}
              exit={{ height: 0, opacity: 0 }}
              className="overflow-hidden"
            >
              <div className="flex flex-wrap items-center gap-4 pt-4 mt-4 border-t border-smoke">
                {/* Status Filter */}
                <div className="flex items-center gap-2">
                  <Filter size={14} className="text-mist" />
                  <select
                    value={filters.status || ''}
                    onChange={(e) =>
                      setFilters({ status: e.target.value as RenderStatusType || undefined })
                    }
                    className="input-field py-2 pr-8 min-w-[140px]"
                  >
                    {statusOptions.map((opt) => (
                      <option key={opt.value} value={opt.value}>
                        {opt.label}
                      </option>
                    ))}
                  </select>
                </div>

                {/* Sort */}
                <div className="flex items-center gap-2">
                  <span className="text-mist text-sm">Sort by:</span>
                  <select
                    value={filters.sortField}
                    onChange={(e) => setFilters({ sortField: e.target.value as SortField })}
                    className="input-field py-2 pr-8 min-w-[100px]"
                  >
                    {sortOptions.map((opt) => (
                      <option key={opt.value} value={opt.value}>
                        {opt.label}
                      </option>
                    ))}
                  </select>
                  <button
                    onClick={() =>
                      setFilters({
                        sortDirection: filters.sortDirection === 'asc' ? 'desc' : 'asc',
                      })
                    }
                    className="p-2 rounded-lg hover:bg-smoke transition-colors text-mist"
                  >
                    {filters.sortDirection === 'asc' ? '↑' : '↓'}
                  </button>
                </div>

                {/* Clear Filters */}
                {hasActiveFilters && (
                  <button
                    onClick={clearFilters}
                    className="text-sm text-violet-400 hover:text-violet-300 transition-colors"
                  >
                    Clear all
                  </button>
                )}
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </motion.div>

      {/* Error State */}
      {error && (
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="glass-card p-6 border-red-500/20 bg-red-500/5"
        >
          <div className="flex items-center gap-3 text-red-400">
            <AlertCircle size={20} />
            <span>{error}</span>
            <button
              onClick={refresh}
              className="ml-auto text-sm underline hover:no-underline"
            >
              Try again
            </button>
          </div>
        </motion.div>
      )}

      {/* Gallery Grid */}
      <motion.div
        variants={containerVariants}
        initial="hidden"
        animate="visible"
        className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6"
      >
        {isLoading ? (
          // Skeleton loaders
          <>
            <SkeletonCard />
            <SkeletonCard />
            <SkeletonCard />
            <SkeletonCard />
            <SkeletonCard />
            <SkeletonCard />
          </>
        ) : filteredRenders.length === 0 ? (
          <EmptyState hasFilters={!!hasActiveFilters} onClear={clearFilters} />
        ) : (
          <AnimatePresence mode="popLayout">
            {filteredRenders.map((render) => (
              <RenderCard
                key={render.id}
                render={render}
                onPlay={() => handlePlay(render)}
                onDownload={() => handleDownload(render)}
                onDelete={() => handleDelete(render)}
              />
            ))}
          </AnimatePresence>
        )}
      </motion.div>

      {/* Results count */}
      {!isLoading && filteredRenders.length > 0 && (
        <motion.p
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          className="text-center text-sm text-mist"
        >
          Showing {filteredRenders.length} of {stats.total} renders
        </motion.p>
      )}
    </div>
  );
}

export default Gallery;
