import { motion } from 'framer-motion';
import { useSortable } from '@dnd-kit/sortable';
import { CSS } from '@dnd-kit/utilities';
import { GripVertical, Trash2, User, Loader2, Check, AlertCircle, Pencil } from 'lucide-react';
import type { Subject } from '../types';

interface SubjectCardProps {
  subject: Subject;
  index: number;
  onRemove: (id: string) => void;
  onEdit: (subject: Subject) => void;
  isAnchor?: boolean;
}

export function SubjectCard({ subject, index, onRemove, onEdit, isAnchor }: SubjectCardProps) {
  const {
    attributes,
    listeners,
    setNodeRef,
    transform,
    transition,
    isDragging,
  } = useSortable({ id: subject.id });

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
  };

  const statusConfig = {
    pending: { icon: <User size={16} />, color: 'text-mist', bg: 'bg-smoke' },
    generating: { icon: <Loader2 size={16} className="animate-spin" />, color: 'text-aurora-start', bg: 'bg-aurora-start/20' },
    completed: { icon: <Check size={16} />, color: 'text-success', bg: 'bg-success/20' },
    error: { icon: <AlertCircle size={16} />, color: 'text-error', bg: 'bg-error/20' },
  };

  const status = statusConfig[subject.status];

  return (
    <motion.div
      ref={setNodeRef}
      style={style}
      layout
      initial={{ opacity: 0, scale: 0.9 }}
      animate={{ 
        opacity: isDragging ? 0.5 : 1, 
        scale: isDragging ? 1.02 : 1,
        boxShadow: isDragging ? '0 24px 48px -12px rgba(0, 0, 0, 0.5)' : 'none'
      }}
      exit={{ opacity: 0, scale: 0.9, y: -20 }}
      transition={{ duration: 0.2 }}
      className={`
        glass-card p-4 flex items-center gap-4 group
        ${isDragging ? 'z-50 ring-2 ring-aurora-start/50' : ''}
        ${isAnchor ? 'border-aurora-start/30' : ''}
      `}
    >
      {/* Drag Handle */}
      <button
        {...attributes}
        {...listeners}
        className="p-2 rounded-lg hover:bg-smoke/50 text-mist hover:text-silver transition-colors cursor-grab active:cursor-grabbing"
      >
        <GripVertical size={18} />
      </button>

      {/* Index Badge */}
      <div className={`
        w-8 h-8 rounded-lg flex items-center justify-center text-sm font-bold
        ${isAnchor 
          ? 'bg-gradient-to-br from-aurora-start to-aurora-mid text-white' 
          : 'bg-smoke text-silver'
        }
      `}>
        {isAnchor ? '★' : index}
      </div>

      {/* Avatar / Generated Image */}
      <div className="relative w-14 h-14 rounded-xl overflow-hidden bg-smoke flex-shrink-0">
        {subject.image_url ? (
          <img 
            src={subject.image_url} 
            alt={subject.name} 
            className="w-full h-full object-cover"
          />
        ) : (
          <div className="w-full h-full flex items-center justify-center">
            <User size={24} className="text-mist" />
          </div>
        )}
        
        {/* Status Overlay */}
        {subject.status === 'generating' && (
          <motion.div
            className="absolute inset-0 bg-obsidian/60 flex items-center justify-center"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
          >
            <Loader2 size={20} className="text-aurora-start animate-spin" />
          </motion.div>
        )}
      </div>

      {/* Content */}
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2 mb-1">
          <h4 className="font-semibold text-snow truncate">{subject.name}</h4>
          {isAnchor && (
            <span className="badge badge-info text-[10px] px-2">ANCHOR</span>
          )}
        </div>
        <p className="text-sm text-mist truncate">{subject.visual_prompt}</p>
      </div>

      {/* Status */}
      <div className={`${status.bg} ${status.color} p-2 rounded-lg`}>
        {status.icon}
      </div>

      {/* Actions */}
      <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
        <button
          onClick={() => onEdit(subject)}
          className="p-2 rounded-lg hover:bg-smoke/50 text-mist hover:text-cloud transition-colors"
        >
          <Pencil size={16} />
        </button>
        {!isAnchor && (
          <button
            onClick={() => onRemove(subject.id)}
            className="p-2 rounded-lg hover:bg-error/20 text-mist hover:text-error transition-colors"
          >
            <Trash2 size={16} />
          </button>
        )}
      </div>
    </motion.div>
  );
}
