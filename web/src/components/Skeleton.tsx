import { motion } from 'framer-motion';

interface SkeletonProps {
  className?: string;
}

export function Skeleton({ className = '' }: SkeletonProps) {
  return (
    <motion.div
      className={`bg-smoke/50 rounded-lg shimmer ${className}`}
      initial={{ opacity: 0.5 }}
      animate={{ opacity: [0.5, 0.8, 0.5] }}
      transition={{ duration: 1.5, repeat: Infinity }}
    />
  );
}

export function SkeletonCard() {
  return (
    <div className="glass-card p-6 space-y-4">
      <div className="flex items-center gap-4">
        <Skeleton className="w-12 h-12 rounded-xl" />
        <div className="flex-1 space-y-2">
          <Skeleton className="h-4 w-3/4" />
          <Skeleton className="h-3 w-1/2" />
        </div>
      </div>
      <Skeleton className="h-20 w-full" />
      <div className="flex gap-2">
        <Skeleton className="h-8 w-20" />
        <Skeleton className="h-8 w-20" />
      </div>
    </div>
  );
}

export function SkeletonSubject() {
  return (
    <div className="glass-card p-4 flex items-center gap-4">
      <Skeleton className="w-6 h-6" />
      <Skeleton className="w-8 h-8 rounded-lg" />
      <Skeleton className="w-14 h-14 rounded-xl" />
      <div className="flex-1 space-y-2">
        <Skeleton className="h-4 w-32" />
        <Skeleton className="h-3 w-48" />
      </div>
      <Skeleton className="w-8 h-8 rounded-lg" />
    </div>
  );
}

export function SkeletonDashboard() {
  return (
    <div className="max-w-7xl mx-auto space-y-8">
      {/* Header */}
      <div className="space-y-2">
        <Skeleton className="h-10 w-64" />
        <Skeleton className="h-5 w-96" />
      </div>

      {/* Grid */}
      <div className="grid grid-cols-12 gap-4 auto-rows-[minmax(140px,auto)]">
        {/* Hero */}
        <div className="col-span-12 lg:col-span-6 row-span-2">
          <SkeletonCard />
        </div>
        
        {/* Stats */}
        {[1, 2, 3, 4].map((i) => (
          <div key={i} className="col-span-6 lg:col-span-3">
            <div className="glass-card p-5 h-full">
              <Skeleton className="w-10 h-10 rounded-xl mb-4" />
              <Skeleton className="h-8 w-16 mb-2" />
              <Skeleton className="h-4 w-24" />
            </div>
          </div>
        ))}

        {/* Recent Projects */}
        <div className="col-span-12 lg:col-span-6 row-span-2">
          <div className="glass-card p-6 h-full space-y-4">
            <Skeleton className="h-6 w-40" />
            {[1, 2, 3].map((i) => (
              <Skeleton key={i} className="h-16" />
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
