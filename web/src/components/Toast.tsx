import { motion, AnimatePresence } from 'framer-motion';
import { Check, AlertCircle, Info, X, AlertTriangle } from 'lucide-react';

export type ToastType = 'success' | 'error' | 'warning' | 'info';

interface ToastProps {
  id: string;
  type: ToastType;
  title: string;
  message?: string;
  onClose: (id: string) => void;
}

const toastConfig = {
  success: {
    icon: <Check size={18} />,
    bg: 'bg-success/20',
    border: 'border-success/30',
    iconBg: 'bg-success',
    text: 'text-success',
  },
  error: {
    icon: <AlertCircle size={18} />,
    bg: 'bg-error/20',
    border: 'border-error/30',
    iconBg: 'bg-error',
    text: 'text-error',
  },
  warning: {
    icon: <AlertTriangle size={18} />,
    bg: 'bg-warning/20',
    border: 'border-warning/30',
    iconBg: 'bg-warning',
    text: 'text-warning',
  },
  info: {
    icon: <Info size={18} />,
    bg: 'bg-aurora-start/20',
    border: 'border-aurora-start/30',
    iconBg: 'bg-aurora-start',
    text: 'text-aurora-start',
  },
};

export function Toast({ id, type, title, message, onClose }: ToastProps) {
  const config = toastConfig[type];

  return (
    <motion.div
      layout
      initial={{ opacity: 0, x: 100, scale: 0.9 }}
      animate={{ opacity: 1, x: 0, scale: 1 }}
      exit={{ opacity: 0, x: 100, scale: 0.9 }}
      transition={{ type: 'spring', damping: 20, stiffness: 300 }}
      className={`
        ${config.bg} ${config.border}
        backdrop-blur-xl border rounded-xl p-4 shadow-float
        flex items-start gap-3 min-w-[320px] max-w-[420px]
      `}
    >
      <div className={`${config.iconBg} p-2 rounded-lg text-white`}>
        {config.icon}
      </div>
      
      <div className="flex-1 min-w-0">
        <p className={`font-semibold ${config.text}`}>{title}</p>
        {message && (
          <p className="text-sm text-silver mt-0.5">{message}</p>
        )}
      </div>
      
      <button
        onClick={() => onClose(id)}
        className="p-1 rounded-lg hover:bg-white/10 text-mist hover:text-cloud transition-colors"
      >
        <X size={16} />
      </button>
    </motion.div>
  );
}

interface ToastContainerProps {
  toasts: Array<{
    id: string;
    type: ToastType;
    title: string;
    message?: string;
  }>;
  onClose: (id: string) => void;
}

export function ToastContainer({ toasts, onClose }: ToastContainerProps) {
  return (
    <div className="fixed bottom-6 right-6 z-[100] flex flex-col gap-3">
      <AnimatePresence mode="popLayout">
        {toasts.map((toast) => (
          <Toast key={toast.id} {...toast} onClose={onClose} />
        ))}
      </AnimatePresence>
    </div>
  );
}
