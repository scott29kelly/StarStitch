import { motion } from 'framer-motion';
import { 
  Sparkles, 
  LayoutDashboard, 
  Settings, 
  Play, 
  Image, 
  History,
  Github,
  ChevronRight
} from 'lucide-react';
import type { View } from '../types';

interface LayoutProps {
  children: React.ReactNode;
  currentView: View;
  onViewChange: (view: View) => void;
}

const navItems: { id: View; label: string; icon: React.ReactNode }[] = [
  { id: 'dashboard', label: 'Dashboard', icon: <LayoutDashboard size={20} /> },
  { id: 'configure', label: 'Configure', icon: <Settings size={20} /> },
  { id: 'render', label: 'Render', icon: <Play size={20} /> },
  { id: 'history', label: 'History', icon: <History size={20} /> },
  { id: 'gallery', label: 'Gallery', icon: <Image size={20} /> },
];

export function Layout({ children, currentView, onViewChange }: LayoutProps) {
  return (
    <div className="min-h-screen bg-void bg-mesh noise">
      {/* Ambient Orbs - Floating background elements */}
      <div className="fixed inset-0 pointer-events-none overflow-hidden">
        <motion.div
          className="absolute top-1/4 left-1/4 w-96 h-96 bg-aurora-start/20 rounded-full blur-3xl"
          animate={{
            x: [0, 50, 0],
            y: [0, 30, 0],
            scale: [1, 1.1, 1],
          }}
          transition={{
            duration: 20,
            repeat: Infinity,
            ease: 'easeInOut',
          }}
        />
        <motion.div
          className="absolute bottom-1/4 right-1/4 w-80 h-80 bg-aurora-mid/15 rounded-full blur-3xl"
          animate={{
            x: [0, -40, 0],
            y: [0, -50, 0],
            scale: [1, 1.2, 1],
          }}
          transition={{
            duration: 25,
            repeat: Infinity,
            ease: 'easeInOut',
          }}
        />
        <motion.div
          className="absolute top-3/4 left-1/2 w-64 h-64 bg-neon-cyan/10 rounded-full blur-3xl"
          animate={{
            x: [0, 60, 0],
            y: [0, -30, 0],
          }}
          transition={{
            duration: 18,
            repeat: Infinity,
            ease: 'easeInOut',
          }}
        />
      </div>

      {/* Sidebar */}
      <motion.aside
        initial={{ x: -100, opacity: 0 }}
        animate={{ x: 0, opacity: 1 }}
        transition={{ duration: 0.5, ease: [0.16, 1, 0.3, 1] }}
        className="fixed left-0 top-0 h-full w-72 z-50"
      >
        <div className="h-full glass-card rounded-none border-l-0 border-t-0 border-b-0 p-6 flex flex-col">
          {/* Logo */}
          <motion.div 
            className="flex items-center gap-3 mb-10"
            initial={{ opacity: 0, y: -20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.2 }}
          >
            <div className="relative">
              <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-aurora-start to-aurora-mid flex items-center justify-center">
                <Sparkles size={22} className="text-white" />
              </div>
              <motion.div
                className="absolute inset-0 rounded-xl bg-gradient-to-br from-aurora-start to-aurora-mid"
                animate={{ scale: [1, 1.2, 1], opacity: [0.5, 0, 0.5] }}
                transition={{ duration: 2, repeat: Infinity }}
              />
            </div>
            <div>
              <h1 className="text-xl font-bold text-snow tracking-tight">StarStitch</h1>
              <p className="text-xs text-mist font-medium">AI Video Morphing</p>
            </div>
          </motion.div>

          {/* Navigation */}
          <nav className="flex-1 space-y-1">
            {navItems.map((item, index) => (
              <motion.button
                key={item.id}
                onClick={() => onViewChange(item.id)}
                initial={{ opacity: 0, x: -20 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: 0.3 + index * 0.1 }}
                className={`
                  w-full flex items-center gap-3 px-4 py-3 rounded-lg
                  transition-all duration-300 group relative overflow-hidden
                  ${currentView === item.id 
                    ? 'bg-gradient-to-r from-aurora-start/20 to-aurora-mid/10 text-snow' 
                    : 'text-silver hover:text-cloud hover:bg-smoke/50'
                  }
                `}
              >
                {currentView === item.id && (
                  <motion.div
                    layoutId="activeNav"
                    className="absolute left-0 top-0 bottom-0 w-1 bg-gradient-to-b from-aurora-start to-aurora-mid rounded-full"
                  />
                )}
                <span className={`transition-transform duration-300 ${currentView === item.id ? 'scale-110' : 'group-hover:scale-110'}`}>
                  {item.icon}
                </span>
                <span className="font-medium">{item.label}</span>
                <ChevronRight 
                  size={16} 
                  className={`
                    ml-auto transition-all duration-300
                    ${currentView === item.id ? 'opacity-100 translate-x-0' : 'opacity-0 -translate-x-2'}
                  `}
                />
              </motion.button>
            ))}
          </nav>

          {/* Footer */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.8 }}
            className="pt-6 border-t border-smoke"
          >
            <a
              href="https://github.com/scott29kelly/StarStitch"
              target="_blank"
              rel="noopener noreferrer"
              className="flex items-center gap-3 px-4 py-3 rounded-lg text-mist hover:text-cloud hover:bg-smoke/50 transition-all duration-300"
            >
              <Github size={18} />
              <span className="text-sm">View on GitHub</span>
            </a>
            <p className="text-xs text-mist/60 mt-4 px-4">
              v0.6.0 — API Backend
            </p>
          </motion.div>
        </div>
      </motion.aside>

      {/* Main Content */}
      <main className="pl-72">
        <div className="min-h-screen p-8">
          <motion.div
            key={currentView}
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -20 }}
            transition={{ duration: 0.4, ease: [0.16, 1, 0.3, 1] }}
          >
            {children}
          </motion.div>
        </div>
      </main>
    </div>
  );
}
