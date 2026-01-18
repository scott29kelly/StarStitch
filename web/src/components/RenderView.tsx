import { useEffect, useState } from 'react';
import { motion } from 'framer-motion';
import { 
  Pause, 
  RefreshCw, 
  Download, 
  Check,
  Loader2,
  AlertCircle,
  Clock,
  Zap,
  Film
} from 'lucide-react';
import type { RenderProgress, Subject } from '../types';

interface RenderViewProps {
  progress: RenderProgress;
  subjects: Subject[];
  onPause?: () => void;
  onRetry?: () => void;
  onDownload?: () => void;
}

export function RenderView({ 
  progress, 
  subjects,
  onPause,
  onRetry,
  onDownload 
}: RenderViewProps) {
  const [elapsedTime, setElapsedTime] = useState(0);

  useEffect(() => {
    if (progress.status === 'rendering') {
      const interval = setInterval(() => {
        setElapsedTime((prev) => prev + 1);
      }, 1000);
      return () => clearInterval(interval);
    }
  }, [progress.status]);

  const formatTime = (seconds: number) => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  const statusConfig = {
    idle: { label: 'Ready', color: 'text-mist', bg: 'bg-smoke' },
    preparing: { label: 'Preparing', color: 'text-warning', bg: 'bg-warning/20' },
    rendering: { label: 'Rendering', color: 'text-aurora-start', bg: 'bg-aurora-start/20' },
    complete: { label: 'Complete', color: 'text-success', bg: 'bg-success/20' },
    error: { label: 'Error', color: 'text-error', bg: 'bg-error/20' },
  };

  const status = statusConfig[progress.status];

  return (
    <div className="max-w-4xl mx-auto space-y-8">
      {/* Header */}
      <div className="text-center">
        <motion.h1 
          className="text-4xl font-bold text-snow mb-2"
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
        >
          {progress.status === 'complete' ? 'Generation Complete!' : 'Generating Your Stitch'}
        </motion.h1>
        <p className="text-silver">
          {progress.status === 'complete' 
            ? 'Your video is ready to download'
            : 'Sit back while we create your morphing masterpiece'
          }
        </p>
      </div>

      {/* Main Progress Card */}
      <motion.div 
        className="glass-card p-8"
        initial={{ opacity: 0, scale: 0.95 }}
        animate={{ opacity: 1, scale: 1 }}
      >
        {/* Status Badge */}
        <div className="flex items-center justify-center mb-8">
          <div className={`${status.bg} ${status.color} px-4 py-2 rounded-full flex items-center gap-2`}>
            {progress.status === 'rendering' ? (
              <Loader2 size={16} className="animate-spin" />
            ) : progress.status === 'complete' ? (
              <Check size={16} />
            ) : progress.status === 'error' ? (
              <AlertCircle size={16} />
            ) : (
              <Clock size={16} />
            )}
            <span className="font-semibold">{status.label}</span>
          </div>
        </div>

        {/* Circular Progress */}
        <div className="relative w-48 h-48 mx-auto mb-8">
          {/* Background Circle */}
          <svg className="w-full h-full transform -rotate-90">
            <circle
              cx="96"
              cy="96"
              r="88"
              stroke="currentColor"
              strokeWidth="8"
              fill="none"
              className="text-smoke"
            />
            <motion.circle
              cx="96"
              cy="96"
              r="88"
              stroke="url(#progressGradient)"
              strokeWidth="8"
              fill="none"
              strokeLinecap="round"
              strokeDasharray={553}
              initial={{ strokeDashoffset: 553 }}
              animate={{ strokeDashoffset: 553 - (553 * progress.progress_percent) / 100 }}
              transition={{ duration: 0.5 }}
            />
            <defs>
              <linearGradient id="progressGradient" x1="0%" y1="0%" x2="100%" y2="0%">
                <stop offset="0%" stopColor="#6366f1" />
                <stop offset="50%" stopColor="#a855f7" />
                <stop offset="100%" stopColor="#ec4899" />
              </linearGradient>
            </defs>
          </svg>
          
          {/* Center Content */}
          <div className="absolute inset-0 flex flex-col items-center justify-center">
            <motion.span 
              className="text-5xl font-bold text-aurora"
              key={progress.progress_percent}
              initial={{ scale: 1.2, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
            >
              {progress.progress_percent}%
            </motion.span>
            <span className="text-sm text-mist mt-1">
              Step {progress.current_step}/{progress.total_steps}
            </span>
          </div>
        </div>

        {/* Current Message */}
        <motion.div 
          className="text-center mb-8"
          key={progress.message}
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
        >
          <p className="text-lg text-cloud">{progress.message}</p>
          {progress.current_subject && (
            <p className="text-sm text-mist mt-1">
              Current: <span className="text-aurora-start font-medium">{progress.current_subject}</span>
            </p>
          )}
        </motion.div>

        {/* Stats Row */}
        <div className="grid grid-cols-3 gap-4">
          <div className="text-center p-4 bg-smoke/30 rounded-xl">
            <Clock size={20} className="mx-auto text-mist mb-2" />
            <p className="text-2xl font-bold text-snow">{formatTime(elapsedTime)}</p>
            <p className="text-xs text-mist">Elapsed</p>
          </div>
          <div className="text-center p-4 bg-smoke/30 rounded-xl">
            <Film size={20} className="mx-auto text-mist mb-2" />
            <p className="text-2xl font-bold text-snow">{subjects.length}</p>
            <p className="text-xs text-mist">Subjects</p>
          </div>
          <div className="text-center p-4 bg-smoke/30 rounded-xl">
            <Zap size={20} className="mx-auto text-mist mb-2" />
            <p className="text-2xl font-bold text-snow">{subjects.length - 1}</p>
            <p className="text-xs text-mist">Morphs</p>
          </div>
        </div>
      </motion.div>

      {/* Subject Progress */}
      <div className="glass-card p-6">
        <h3 className="text-sm font-semibold text-silver uppercase tracking-wider mb-4">
          Generation Queue
        </h3>
        <div className="space-y-3">
          {subjects.map((subject, index) => (
            <motion.div
              key={subject.id}
              initial={{ opacity: 0, x: -20 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: index * 0.1 }}
              className={`
                flex items-center gap-4 p-4 rounded-xl
                ${subject.status === 'completed' 
                  ? 'bg-success/10 border border-success/20' 
                  : subject.status === 'generating'
                    ? 'bg-aurora-start/10 border border-aurora-start/20'
                    : 'bg-smoke/30'
                }
              `}
            >
              <div className={`
                w-8 h-8 rounded-lg flex items-center justify-center text-sm font-bold
                ${subject.status === 'completed' 
                  ? 'bg-success text-white' 
                  : subject.status === 'generating'
                    ? 'bg-aurora-start text-white'
                    : 'bg-smoke text-mist'
                }
              `}>
                {subject.status === 'completed' ? (
                  <Check size={16} />
                ) : subject.status === 'generating' ? (
                  <Loader2 size={16} className="animate-spin" />
                ) : (
                  index + 1
                )}
              </div>
              
              <div className="flex-1">
                <p className={`font-medium ${subject.status === 'completed' ? 'text-success' : subject.status === 'generating' ? 'text-aurora-start' : 'text-cloud'}`}>
                  {subject.name}
                </p>
                <p className="text-xs text-mist truncate">{subject.visual_prompt}</p>
              </div>

              {index === 0 && (
                <span className="text-xs px-2 py-1 bg-aurora-start/20 text-aurora-start rounded">
                  ANCHOR
                </span>
              )}
            </motion.div>
          ))}
        </div>
      </div>

      {/* Action Buttons */}
      <div className="flex items-center justify-center gap-4">
        {progress.status === 'rendering' && onPause && (
          <button onClick={onPause} className="btn-ghost flex items-center gap-2">
            <Pause size={18} />
            Pause
          </button>
        )}
        
        {progress.status === 'error' && onRetry && (
          <button onClick={onRetry} className="btn-glow flex items-center gap-2">
            <RefreshCw size={18} />
            Retry
          </button>
        )}
        
        {progress.status === 'complete' && onDownload && (
          <motion.button
            onClick={onDownload}
            className="btn-glow flex items-center gap-2 px-8 py-4"
            initial={{ scale: 0 }}
            animate={{ scale: 1 }}
            transition={{ type: 'spring', delay: 0.3 }}
          >
            <Download size={20} />
            Download Video
          </motion.button>
        )}
      </div>
    </div>
  );
}
