import { motion } from 'framer-motion';
import { 
  Film, 
  Download, 
  Trash2, 
  Calendar,
  Users,
  Play
} from 'lucide-react';

interface Project {
  id: string;
  name: string;
  date: string;
  duration: string;
  subjects: number;
  thumbnail?: string;
  status: 'complete' | 'error';
}

interface GalleryProps {
  projects: Project[];
  onDelete: (id: string) => void;
  onDownload: (id: string) => void;
  onPlay: (id: string) => void;
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
  visible: { opacity: 1, y: 0 }
};

export function Gallery({ projects, onDelete, onDownload, onPlay }: GalleryProps) {
  if (projects.length === 0) {
    return (
      <div className="max-w-4xl mx-auto">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="glass-card p-16 text-center"
        >
          <motion.div
            className="w-24 h-24 rounded-full bg-smoke/50 flex items-center justify-center mx-auto mb-6"
            animate={{ scale: [1, 1.05, 1] }}
            transition={{ duration: 3, repeat: Infinity }}
          >
            <Film size={40} className="text-mist" />
          </motion.div>
          <h2 className="text-2xl font-bold text-snow mb-2">No Projects Yet</h2>
          <p className="text-silver max-w-md mx-auto">
            Your completed stitches will appear here. Start by creating a new project
            and let the AI work its magic.
          </p>
        </motion.div>
      </div>
    );
  }

  return (
    <div className="max-w-6xl mx-auto">
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        className="mb-8"
      >
        <h1 className="text-3xl font-bold text-snow mb-2">Your Gallery</h1>
        <p className="text-silver">
          {projects.length} completed {projects.length === 1 ? 'project' : 'projects'}
        </p>
      </motion.div>

      <motion.div
        variants={containerVariants}
        initial="hidden"
        animate="visible"
        className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6"
      >
        {projects.map((project) => (
          <motion.div
            key={project.id}
            variants={itemVariants}
            className="glass-card-hover group cursor-pointer overflow-hidden"
            onClick={() => onPlay(project.id)}
          >
            {/* Thumbnail */}
            <div className="relative aspect-video bg-smoke overflow-hidden">
              {project.thumbnail ? (
                <img 
                  src={project.thumbnail} 
                  alt={project.name}
                  className="w-full h-full object-cover transition-transform duration-500 group-hover:scale-105"
                />
              ) : (
                <div className="w-full h-full flex items-center justify-center bg-gradient-to-br from-aurora-start/20 to-aurora-mid/20">
                  <Film size={48} className="text-mist" />
                </div>
              )}
              
              {/* Play Overlay */}
              <div className="absolute inset-0 bg-obsidian/60 opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center">
                <motion.div
                  className="w-16 h-16 rounded-full bg-white/20 backdrop-blur-sm flex items-center justify-center"
                  whileHover={{ scale: 1.1 }}
                  whileTap={{ scale: 0.95 }}
                >
                  <Play size={28} className="text-white ml-1" />
                </motion.div>
              </div>

              {/* Duration Badge */}
              <div className="absolute bottom-3 right-3 bg-obsidian/80 backdrop-blur-sm px-2 py-1 rounded text-xs text-cloud font-mono">
                {project.duration}
              </div>

              {/* Status Badge */}
              {project.status === 'error' && (
                <div className="absolute top-3 left-3 bg-error/90 px-2 py-1 rounded text-xs text-white font-medium">
                  Failed
                </div>
              )}
            </div>

            {/* Content */}
            <div className="p-5">
              <h3 className="font-bold text-snow text-lg mb-2 group-hover:text-aurora transition-colors">
                {project.name}
              </h3>
              
              <div className="flex items-center gap-4 text-sm text-mist mb-4">
                <span className="flex items-center gap-1">
                  <Calendar size={14} />
                  {project.date}
                </span>
                <span className="flex items-center gap-1">
                  <Users size={14} />
                  {project.subjects}
                </span>
              </div>

              {/* Actions */}
              <div className="flex items-center gap-2 pt-4 border-t border-smoke">
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    onDownload(project.id);
                  }}
                  className="flex-1 flex items-center justify-center gap-2 py-2 rounded-lg bg-smoke/50 hover:bg-smoke text-cloud transition-colors"
                >
                  <Download size={16} />
                  <span className="text-sm">Download</span>
                </button>
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    onDelete(project.id);
                  }}
                  className="p-2 rounded-lg hover:bg-error/20 text-mist hover:text-error transition-colors"
                >
                  <Trash2 size={16} />
                </button>
              </div>
            </div>
          </motion.div>
        ))}
      </motion.div>
    </div>
  );
}
