import { useState, useEffect } from 'react';
import { AnimatePresence } from 'framer-motion';
import { Layout, Dashboard, ConfigurePanel, RenderView, Gallery, ToastContainer } from './components';
import { useToast, useRender } from './hooks';
import type { View, ProjectConfig, Subject } from './types';
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

// Mock recent projects (will be replaced with API data in future)
const mockRecentProjects = [
  { name: 'Eiffel Tower Stars', date: 'Jan 17, 2026', status: 'complete' as const },
  { name: 'Tech Legends', date: 'Jan 15, 2026', status: 'complete' as const },
  { name: 'Hollywood Icons', date: 'Jan 12, 2026', status: 'draft' as const },
];

function App() {
  const [currentView, setCurrentView] = useState<View>('dashboard');
  const [config, setConfig] = useState<ProjectConfig>(defaultConfig);

  const toast = useToast();

  // Use the real render hook for API integration
  const render = useRender();

  // Update subject statuses based on render progress
  useEffect(() => {
    if (render.progress.status === 'rendering' && render.progress.current_subject) {
      const subjectName = render.progress.current_subject;
      setConfig((prev) => ({
        ...prev,
        sequence: prev.sequence.map((s) => {
          if (s.name === subjectName) {
            return { ...s, status: 'generating' as const };
          }
          // Mark previous subjects as completed
          const currentIndex = prev.sequence.findIndex((seq) => seq.name === subjectName);
          const thisIndex = prev.sequence.findIndex((seq) => seq.name === s.name);
          if (thisIndex < currentIndex) {
            return { ...s, status: 'completed' as const };
          }
          return s;
        }),
      }));
    } else if (render.progress.status === 'complete') {
      setConfig((prev) => ({
        ...prev,
        sequence: prev.sequence.map((s) => ({ ...s, status: 'completed' as const })),
      }));
    }
  }, [render.progress.current_subject, render.progress.status]);

  // Show toast notifications based on render state
  useEffect(() => {
    if (render.state === 'rendering' && render.progress.current_step === 1) {
      toast.info('Starting Generation', 'Your stitch is being prepared...');
    } else if (render.state === 'complete') {
      toast.success('Generation Complete!', 'Your video is ready to download.');
    } else if (render.state === 'error' && render.error) {
      toast.error('Generation Failed', render.error);
    } else if (render.state === 'cancelled') {
      toast.warning('Generation Cancelled', 'The render was cancelled.');
    }
  }, [render.state, render.progress.current_step, render.error, toast]);

  const handleStartNew = () => {
    setConfig(defaultConfig);
    render.reset();
    setCurrentView('configure');
  };

  const handleStartRender = async () => {
    setCurrentView('render');
    // Reset subjects to pending
    setConfig((prev) => ({
      ...prev,
      sequence: prev.sequence.map((s) => ({ ...s, status: 'pending' as const })),
    }));
    // Start the real render via API
    await render.startRender(config);
  };

  const handlePauseRender = async () => {
    await render.cancelRender();
    toast.info('Paused', 'Generation has been paused.');
  };

  const handleRetryRender = async () => {
    render.reset();
    await render.startRender(config);
  };

  const handleDownload = () => {
    toast.success('Download Started', 'Your video is being downloaded...');
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
              renderProgress={render.progress.status !== 'idle' ? render.progress : undefined}
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
              progress={render.progress}
              subjects={config.sequence}
              onPause={handlePauseRender}
              onRetry={handleRetryRender}
              onDownload={handleDownload}
            />
          )}

          {currentView === 'gallery' && (
            <Gallery key="gallery" />
          )}
        </AnimatePresence>
      </Layout>
      
      <ToastContainer toasts={toast.toasts} onClose={toast.removeToast} />
    </>
  );
}

export default App;
