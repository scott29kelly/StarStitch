import { motion } from 'framer-motion';
import { 
  Zap, 
  Clock, 
  Film, 
  Sparkles, 
  TrendingUp,
  ArrowRight,
  Play
} from 'lucide-react';
import type { RenderProgress } from '../types';

interface DashboardProps {
  onStartNew: () => void;
  recentProjects: { name: string; date: string; status: 'complete' | 'draft' }[];
  renderProgress?: RenderProgress;
}

const containerVariants = {
  hidden: { opacity: 0 },
  visible: {
    opacity: 1,
    transition: { staggerChildren: 0.1 }
  }
};

const itemVariants = {
  hidden: { opacity: 0, y: 20 },
  visible: { opacity: 1, y: 0, transition: { duration: 0.5, ease: [0.16, 1, 0.3, 1] as const } }
};

export function Dashboard({ onStartNew, recentProjects, renderProgress }: DashboardProps) {
  const stats = [
    { label: 'Projects Created', value: '12', icon: <Film size={20} />, color: 'from-aurora-start to-aurora-mid' },
    { label: 'Videos Rendered', value: '47', icon: <Zap size={20} />, color: 'from-neon-cyan to-neon-emerald' },
    { label: 'Time Saved', value: '18h', icon: <Clock size={20} />, color: 'from-aurora-mid to-aurora-end' },
    { label: 'API Credits', value: '2.4K', icon: <TrendingUp size={20} />, color: 'from-warning to-aurora-end' },
  ];

  return (
    <motion.div
      variants={containerVariants}
      initial="hidden"
      animate="visible"
      className="max-w-7xl mx-auto"
    >
      {/* Header */}
      <motion.div variants={itemVariants} className="mb-8">
        <h1 className="text-4xl font-bold text-snow tracking-tight mb-2">
          Welcome back
        </h1>
        <p className="text-silver text-lg">
          Create seamless AI-powered morphing videos in minutes.
        </p>
      </motion.div>

      {/* Bento Grid */}
      <div className="grid grid-cols-12 gap-4 auto-rows-[minmax(140px,auto)]">
        
        {/* Hero Card - New Project */}
        <motion.div 
          variants={itemVariants}
          className="col-span-12 lg:col-span-6 row-span-2"
        >
          <div className="glass-card h-full p-8 relative overflow-hidden group cursor-pointer" onClick={onStartNew}>
            {/* Animated gradient background */}
            <div className="absolute inset-0 bg-gradient-to-br from-aurora-start/20 via-aurora-mid/10 to-transparent opacity-60" />
            <motion.div
              className="absolute top-0 right-0 w-96 h-96 bg-aurora-mid/20 rounded-full blur-3xl"
              animate={{ scale: [1, 1.2, 1], rotate: [0, 90, 0] }}
              transition={{ duration: 20, repeat: Infinity }}
            />
            
            <div className="relative z-10 h-full flex flex-col">
              <div className="flex-1">
                <div className="w-14 h-14 rounded-2xl bg-gradient-to-br from-aurora-start to-aurora-mid flex items-center justify-center mb-6 shadow-glow">
                  <Sparkles size={28} className="text-white" />
                </div>
                <h2 className="text-2xl font-bold text-snow mb-3">
                  Create New Stitch
                </h2>
                <p className="text-silver max-w-sm">
                  Start a new morphing project. Define your subjects and watch the magic happen.
                </p>
              </div>
              
              <motion.div 
                className="flex items-center gap-2 text-aurora-start font-semibold"
                whileHover={{ x: 5 }}
              >
                Get Started
                <ArrowRight size={18} className="group-hover:translate-x-1 transition-transform" />
              </motion.div>
            </div>
          </div>
        </motion.div>

        {/* Stats Grid */}
        {stats.map((stat) => (
          <motion.div
            key={stat.label}
            variants={itemVariants}
            className="col-span-6 lg:col-span-3"
          >
            <div className="glass-card-hover h-full p-5 cursor-default">
              <div className={`w-10 h-10 rounded-xl bg-gradient-to-br ${stat.color} flex items-center justify-center mb-4 opacity-80`}>
                {stat.icon}
              </div>
              <p className="text-3xl font-bold text-snow mb-1">{stat.value}</p>
              <p className="text-sm text-mist">{stat.label}</p>
            </div>
          </motion.div>
        ))}

        {/* Render Progress */}
        {renderProgress && renderProgress.status !== 'idle' && (
          <motion.div
            variants={itemVariants}
            className="col-span-12 lg:col-span-6"
          >
            <div className="glass-card p-6 border-aurora-start/30">
              <div className="flex items-center justify-between mb-4">
                <div className="flex items-center gap-3">
                  <div className="relative">
                    <div className="w-10 h-10 rounded-full bg-aurora-start/20 flex items-center justify-center">
                      <Play size={18} className="text-aurora-start ml-0.5" />
                    </div>
                    {renderProgress.status === 'rendering' && (
                      <motion.div
                        className="absolute inset-0 rounded-full border-2 border-aurora-start"
                        animate={{ scale: [1, 1.3, 1], opacity: [1, 0, 1] }}
                        transition={{ duration: 1.5, repeat: Infinity }}
                      />
                    )}
                  </div>
                  <div>
                    <p className="font-semibold text-snow">Rendering in Progress</p>
                    <p className="text-sm text-mist">
                      Step {renderProgress.current_step} of {renderProgress.total_steps}
                    </p>
                  </div>
                </div>
                <span className="text-aurora-start font-mono text-sm">
                  {renderProgress.progress_percent}%
                </span>
              </div>
              
              {/* Progress Bar */}
              <div className="h-2 bg-smoke rounded-full overflow-hidden">
                <motion.div
                  className="h-full bg-gradient-to-r from-aurora-start to-aurora-mid rounded-full"
                  initial={{ width: 0 }}
                  animate={{ width: `${renderProgress.progress_percent}%` }}
                  transition={{ duration: 0.5 }}
                />
              </div>
              
              <p className="text-sm text-mist mt-3">
                {renderProgress.message}
              </p>
            </div>
          </motion.div>
        )}

        {/* Recent Projects */}
        <motion.div
          variants={itemVariants}
          className="col-span-12 lg:col-span-6 row-span-2"
        >
          <div className="glass-card h-full p-6">
            <h3 className="text-lg font-semibold text-snow mb-4">Recent Projects</h3>
            <div className="space-y-3">
              {recentProjects.length === 0 ? (
                <div className="text-center py-8">
                  <div className="w-16 h-16 rounded-full bg-smoke/50 flex items-center justify-center mx-auto mb-4">
                    <Film size={24} className="text-mist" />
                  </div>
                  <p className="text-mist">No projects yet</p>
                  <p className="text-sm text-mist/60">Create your first stitch to get started</p>
                </div>
              ) : (
                recentProjects.map((project, index) => (
                  <motion.div
                    key={project.name}
                    initial={{ opacity: 0, x: -20 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ delay: 0.5 + index * 0.1 }}
                    className="flex items-center justify-between p-4 rounded-lg bg-smoke/30 hover:bg-smoke/50 transition-colors cursor-pointer group"
                  >
                    <div className="flex items-center gap-3">
                      <div className="w-10 h-10 rounded-lg bg-gradient-to-br from-aurora-start/30 to-aurora-mid/30 flex items-center justify-center">
                        <Film size={18} className="text-aurora-start" />
                      </div>
                      <div>
                        <p className="font-medium text-cloud group-hover:text-snow transition-colors">
                          {project.name}
                        </p>
                        <p className="text-xs text-mist">{project.date}</p>
                      </div>
                    </div>
                    <span className={`badge ${project.status === 'complete' ? 'badge-success' : 'badge-warning'}`}>
                      {project.status}
                    </span>
                  </motion.div>
                ))
              )}
            </div>
          </div>
        </motion.div>

        {/* Quick Tips */}
        <motion.div
          variants={itemVariants}
          className="col-span-12 lg:col-span-6"
        >
          <div className="glass-card p-6">
            <h3 className="text-lg font-semibold text-snow mb-4">Pro Tips</h3>
            <div className="grid grid-cols-2 gap-3">
              {[
                { tip: 'Use detailed prompts for better likeness', icon: '✨' },
                { tip: 'Keep transition duration 4-6s for smoothness', icon: '⏱️' },
                { tip: 'Similar angles help morphing quality', icon: '📐' },
                { tip: 'Golden hour lighting = best results', icon: '🌅' },
              ].map((item, index) => (
                <div key={index} className="flex items-start gap-2 p-3 rounded-lg bg-smoke/30">
                  <span className="text-lg">{item.icon}</span>
                  <p className="text-sm text-silver">{item.tip}</p>
                </div>
              ))}
            </div>
          </div>
        </motion.div>
      </div>
    </motion.div>
  );
}
