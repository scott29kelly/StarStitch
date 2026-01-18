import { motion } from 'framer-motion';
import type { LucideIcon } from 'lucide-react';

interface EmptyStateProps {
  icon: LucideIcon;
  title: string;
  description: string;
  action?: {
    label: string;
    onClick: () => void;
  };
}

export function EmptyState({ icon: Icon, title, description, action }: EmptyStateProps) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className="glass-card p-12 text-center"
    >
      <motion.div
        className="w-20 h-20 rounded-full bg-smoke/50 flex items-center justify-center mx-auto mb-6"
        animate={{ 
          scale: [1, 1.05, 1],
          rotate: [0, 5, -5, 0]
        }}
        transition={{ 
          duration: 4, 
          repeat: Infinity,
          ease: 'easeInOut'
        }}
      >
        <Icon size={36} className="text-mist" />
      </motion.div>
      
      <h2 className="text-xl font-bold text-snow mb-2">{title}</h2>
      <p className="text-silver max-w-sm mx-auto mb-6">{description}</p>
      
      {action && (
        <motion.button
          onClick={action.onClick}
          className="btn-glow"
          whileHover={{ scale: 1.02 }}
          whileTap={{ scale: 0.98 }}
        >
          {action.label}
        </motion.button>
      )}
    </motion.div>
  );
}
