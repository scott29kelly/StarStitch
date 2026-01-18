import { useState } from 'react';
import { AnimatePresence } from 'framer-motion';
import { Layout, Dashboard, ConfigurePanel, RenderView, Gallery, ToastContainer } from './components';
import { useToast } from './hooks';
import type { View, ProjectConfig, RenderProgress } from './types';
import './index.css';

// Default configuration
const defaultConfig: ProjectConfig = {
  project_name: 'my_first_stitch',
  output_folder: 'renders',
  settings: {
    aspect_ratio: '9:16',
    transition_duration_sec: 5,
    image_model: 'black-forest-labs/flux-1.1-pro',
    video_model: 'fal-ai/kling-video/v1.6/pro/image-to-video',
  },
  global_scene: {
    location_prompt: 'taking a selfie at the Eiffel Tower, golden hour lighting, 4k photorealistic',
    negative_prompt: 'blurry, distorted, cartoon, low quality',
  },
  sequence: [
    {
      id: 'anchor',
      name: 'Tourist',
      visual_prompt: 'A friendly tourist in casual clothes, smiling broadly',
      status: 'pending',
    },
  ],
};

// Mock recent projects
const mockRecentProjects = [
  { name: 'Eiffel Tower Stars', date: 'Jan 17, 2026', status: 'complete' as const },
  { name: 'Tech Legends', date: 'Jan 15, 2026', status: 'complete' as const },
  { name: 'Hollywood Icons', date: 'Jan 12, 2026', status: 'draft' as const },
];

// Mock gallery projects
const mockGalleryProjects = [
  { 
    id: '1', 
    name: 'Eiffel Tower Stars', 
    date: 'Jan 17, 2026', 
    duration: '0:25',
    subjects: 5,
    status: 'complete' as const,
  },
  { 
    id: '2', 
    name: 'Tech Legends', 
    date: 'Jan 15, 2026', 
    duration: '0:30',
    subjects: 6,
    status: 'complete' as const,
  },
];

function App() {
  const [currentView, setCurrentView] = useState<View>('dashboard');
  const [config, setConfig] = useState<ProjectConfig>(defaultConfig);
  const [renderProgress, setRenderProgress] = useState<RenderProgress>({
    status: 'idle',
    current_step: 0,
    total_steps: 0,
    progress_percent: 0,
    message: '',
    elapsed_time: 0,
  });
  
  const toast = useToast();

  // Simulate render progress for demo
  const simulateRender = () => {
    const totalSteps = config.sequence.length * 2 + 1; // images + videos + final
    let step = 0;
    
    toast.info('Starting Generation', 'Your stitch is being prepared...');
    
    setRenderProgress({
      status: 'preparing',
      current_step: 0,
      total_steps: totalSteps,
      progress_percent: 0,
      message: 'Preparing workspace...',
      elapsed_time: 0,
    });

    // Update subjects to pending
    setConfig((prev) => ({
      ...prev,
      sequence: prev.sequence.map((s) => ({ ...s, status: 'pending' as const })),
    }));

    const progressInterval = setInterval(() => {
      step++;
      const progress = Math.min(Math.round((step / totalSteps) * 100), 100);
      const subjectIndex = Math.floor((step - 1) / 2);
      const currentSubject = config.sequence[subjectIndex];
      
      if (step <= config.sequence.length) {
        // Generating images
        setRenderProgress({
          status: 'rendering',
          current_step: step,
          total_steps: totalSteps,
          progress_percent: progress,
          message: `Generating image for ${currentSubject?.name || 'subject'}...`,
          current_subject: currentSubject?.name,
          elapsed_time: step * 3,
        });

        // Update subject status
        if (currentSubject) {
          setConfig((prev) => ({
            ...prev,
            sequence: prev.sequence.map((s, i) => 
              i === subjectIndex 
                ? { ...s, status: 'generating' as const } 
                : i < subjectIndex 
                  ? { ...s, status: 'completed' as const }
                  : s
            ),
          }));
        }
      } else if (step <= config.sequence.length * 2) {
        // Generating morphs
        const morphIndex = step - config.sequence.length - 1;
        setRenderProgress({
          status: 'rendering',
          current_step: step,
          total_steps: totalSteps,
          progress_percent: progress,
          message: `Creating morph transition ${morphIndex + 1}...`,
          current_subject: `Morph ${morphIndex + 1}`,
          elapsed_time: step * 3,
        });

        // Mark all subjects as completed
        setConfig((prev) => ({
          ...prev,
          sequence: prev.sequence.map((s) => ({ ...s, status: 'completed' as const })),
        }));
      } else {
        // Finalizing
        setRenderProgress({
          status: 'rendering',
          current_step: step,
          total_steps: totalSteps,
          progress_percent: progress,
          message: 'Concatenating final video...',
          elapsed_time: step * 3,
        });
      }

      if (step >= totalSteps) {
        clearInterval(progressInterval);
        setTimeout(() => {
          setRenderProgress({
            status: 'complete',
            current_step: totalSteps,
            total_steps: totalSteps,
            progress_percent: 100,
            message: 'Your stitch is ready!',
            elapsed_time: totalSteps * 3,
          });
          toast.success('Generation Complete!', 'Your video is ready to download.');
        }, 1000);
      }
    }, 2000);
  };

  const handleStartNew = () => {
    setConfig(defaultConfig);
    setCurrentView('configure');
  };

  const handleStartRender = () => {
    setCurrentView('render');
    simulateRender();
  };

  const handleDownload = () => {
    toast.success('Download Started', 'Your video is being downloaded...');
  };

  const handleDeleteProject = (id: string) => {
    toast.warning('Project Deleted', `Project ${id} has been removed.`);
  };

  return (
    <>
      <Layout currentView={currentView} onViewChange={setCurrentView}>
        <AnimatePresence mode="wait">
          {currentView === 'dashboard' && (
            <Dashboard
              key="dashboard"
              onStartNew={handleStartNew}
              recentProjects={mockRecentProjects}
              renderProgress={renderProgress.status !== 'idle' ? renderProgress : undefined}
            />
          )}

          {currentView === 'configure' && (
            <ConfigurePanel
              key="configure"
              config={config}
              onConfigChange={setConfig}
              onStartRender={handleStartRender}
            />
          )}

          {currentView === 'render' && (
            <RenderView
              key="render"
              progress={renderProgress}
              subjects={config.sequence}
              onPause={() => toast.info('Paused', 'Generation has been paused.')}
              onRetry={simulateRender}
              onDownload={handleDownload}
            />
          )}

          {currentView === 'gallery' && (
            <Gallery
              key="gallery"
              projects={mockGalleryProjects}
              onDelete={handleDeleteProject}
              onDownload={handleDownload}
              onPlay={(id) => toast.info('Playing', `Opening video ${id}...`)}
            />
          )}
        </AnimatePresence>
      </Layout>
      
      <ToastContainer toasts={toast.toasts} onClose={toast.removeToast} />
    </>
  );
}

export default App;
