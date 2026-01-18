import { useState, useEffect, useCallback } from 'react';
import { AnimatePresence } from 'framer-motion';
import { 
  Layout, 
  Dashboard, 
  ConfigurePanel, 
  RenderView, 
  Gallery, 
  RenderHistory,
  ToastContainer 
} from './components';
import { useToast, useRenderWebSocket } from './hooks';
import { api } from './api/client';
import type { View, ProjectConfig, RenderProgress, RenderJob } from './types';
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
    variants: [],
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
  
  // Current job ID for WebSocket connection
  const [currentJobId, setCurrentJobId] = useState<string | null>(null);
  
  // Render history state
  const [renderJobs, setRenderJobs] = useState<RenderJob[]>([]);
  const [isLoadingJobs, setIsLoadingJobs] = useState(false);
  const [jobsHasMore, setJobsHasMore] = useState(false);
  const [jobsPage, setJobsPage] = useState(1);
  
  // Recent projects for dashboard
  const [recentProjects, setRecentProjects] = useState<
    { name: string; date: string; status: 'complete' | 'draft' | 'running' }[]
  >([]);
  
  // Gallery projects
  const [galleryProjects, setGalleryProjects] = useState<
    { id: string; name: string; date: string; duration: string; subjects: number; status: 'complete' }[]
  >([]);

  const toast = useToast();

  // WebSocket connection for real-time updates
  const { 
    renderState, 
    connect: connectWs, 
    cancel: cancelWs,
  } = useRenderWebSocket(
    // On complete
    () => {
      setRenderProgress(prev => ({
        ...prev,
        status: 'complete',
        progress_percent: 100,
        message: 'Your stitch is ready!',
      }));
      
      // Update subjects to completed
      setConfig(prev => ({
        ...prev,
        sequence: prev.sequence.map(s => ({ ...s, status: 'completed' as const })),
      }));
      
      toast.success('Generation Complete!', 'Your video is ready to download.');
      
      // Refresh job list
      loadRenderJobs();
    },
    // On error
    (error) => {
      setRenderProgress(prev => ({
        ...prev,
        status: 'error',
        message: error,
      }));
      toast.error('Generation Failed', error);
    }
  );

  // Update progress from WebSocket
  useEffect(() => {
    if (renderState?.progress) {
      setRenderProgress({
        status: renderState.state === 'running' ? 'rendering' : 
                renderState.state === 'complete' ? 'complete' :
                renderState.state === 'failed' ? 'error' :
                renderState.state === 'cancelled' ? 'cancelled' : 'preparing',
        current_step: renderState.progress.step,
        total_steps: renderState.progress.total_steps,
        progress_percent: renderState.progress.progress_percent,
        message: renderState.progress.message,
        current_subject: renderState.progress.current_subject,
        elapsed_time: renderState.progress.elapsed_seconds,
        estimated_remaining: renderState.progress.estimated_remaining_seconds,
      });
    }
  }, [renderState]);

  // Load render jobs
  const loadRenderJobs = useCallback(async (page = 1) => {
    setIsLoadingJobs(true);
    try {
      const response = await api.listRenders(page, 20);
      
      const jobs: RenderJob[] = response.renders.map(r => ({
        job_id: r.job_id,
        project_name: r.project_name,
        state: r.state,
        created_at: r.created_at,
        completed_at: r.completed_at,
        output_path: r.output_path,
        subjects_count: r.subjects_count,
        progress_percent: r.progress_percent,
      }));
      
      if (page === 1) {
        setRenderJobs(jobs);
      } else {
        setRenderJobs(prev => [...prev, ...jobs]);
      }
      
      setJobsHasMore(response.has_more);
      setJobsPage(page);
      
      // Update recent projects for dashboard
      const recent = jobs.slice(0, 3).map(j => ({
        name: j.project_name,
        date: new Date(j.created_at).toLocaleDateString('en-US', { 
          month: 'short', 
          day: 'numeric', 
          year: 'numeric' 
        }),
        status: j.state === 'running' ? 'running' as const : 
                j.state === 'complete' ? 'complete' as const : 'draft' as const,
      }));
      setRecentProjects(recent);
      
      // Update gallery with completed projects
      const gallery = jobs
        .filter(j => j.state === 'complete')
        .slice(0, 6)
        .map(j => ({
          id: j.job_id,
          name: j.project_name,
          date: new Date(j.created_at).toLocaleDateString('en-US', { 
            month: 'short', 
            day: 'numeric', 
            year: 'numeric' 
          }),
          duration: `0:${j.subjects_count * 5}`,
          subjects: j.subjects_count,
          status: 'complete' as const,
        }));
      setGalleryProjects(gallery);
      
    } catch (error) {
      console.error('Failed to load render jobs:', error);
      toast.error('Failed to Load', 'Could not load render history');
    } finally {
      setIsLoadingJobs(false);
    }
  }, [toast]);

  // Load jobs on mount
  useEffect(() => {
    loadRenderJobs();
  }, [loadRenderJobs]);

  // Start a render via API
  const handleStartRender = async () => {
    try {
      toast.info('Starting Generation', 'Submitting your render job...');
      
      // Prepare request
      const request = {
        project_name: config.project_name,
        output_folder: config.output_folder,
        settings: {
          aspect_ratio: config.settings.aspect_ratio,
          transition_duration_sec: config.settings.transition_duration_sec,
          image_model: config.settings.image_model,
          video_model: config.settings.video_model,
          variants: config.settings.variants || [],
        },
        global_scene: config.global_scene,
        sequence: config.sequence.map(s => ({
          id: s.id,
          name: s.name,
          visual_prompt: s.visual_prompt,
        })),
        audio: config.audio,
      };
      
      const response = await api.startRender(request);
      
      setCurrentJobId(response.job_id);
      setCurrentView('render');
      
      setRenderProgress({
        status: 'preparing',
        current_step: 0,
        total_steps: config.sequence.length * 2 + 1,
        progress_percent: 0,
        message: 'Preparing workspace...',
        elapsed_time: 0,
      });
      
      // Update subjects to pending
      setConfig(prev => ({
        ...prev,
        sequence: prev.sequence.map(s => ({ ...s, status: 'pending' as const })),
      }));
      
      // Connect to WebSocket
      connectWs(response.websocket_url);
      
      toast.success('Job Submitted', `Job ${response.job_id} is now processing`);
      
    } catch (error) {
      console.error('Failed to start render:', error);
      toast.error('Failed to Start', String(error));
    }
  };

  // Cancel render
  const handleCancelRender = async () => {
    if (!currentJobId) return;
    
    try {
      await api.cancelRender(currentJobId);
      cancelWs();
      
      setRenderProgress(prev => ({
        ...prev,
        status: 'cancelled',
        message: 'Render cancelled',
      }));
      
      toast.warning('Cancelled', 'Render job has been cancelled');
      loadRenderJobs();
      
    } catch (error) {
      console.error('Failed to cancel render:', error);
      toast.error('Failed to Cancel', String(error));
    }
  };

  // Delete job from history
  const handleDeleteJob = async (jobId: string) => {
    try {
      await api.deleteRender(jobId);
      setRenderJobs(prev => prev.filter(j => j.job_id !== jobId));
      toast.success('Deleted', 'Job removed from history');
    } catch (error) {
      console.error('Failed to delete job:', error);
      toast.error('Failed to Delete', String(error));
    }
  };

  const handleStartNew = () => {
    setConfig(defaultConfig);
    setCurrentView('configure');
  };

  const handleDownload = (jobId?: string, outputPath?: string) => {
    if (outputPath) {
      // In a real app, this would download the file
      window.open(`/renders/${outputPath.split('/').pop()}`, '_blank');
    }
    toast.success('Download Started', 'Your video is being downloaded...');
  };

  const handleViewJobDetails = async (jobId: string) => {
    try {
      const status = await api.getRenderStatus(jobId);
      console.log('Job details:', status);
      // Could open a modal with details
    } catch (error) {
      console.error('Failed to get job details:', error);
    }
  };

  return (
    <>
      <Layout currentView={currentView} onViewChange={setCurrentView}>
        <AnimatePresence mode="wait">
          {currentView === 'dashboard' && (
            <Dashboard
              key="dashboard"
              onStartNew={handleStartNew}
              recentProjects={recentProjects}
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
              onPause={handleCancelRender}
              onRetry={handleStartRender}
              onDownload={() => handleDownload()}
            />
          )}

          {currentView === 'history' && (
            <RenderHistory
              key="history"
              jobs={renderJobs}
              isLoading={isLoadingJobs}
              onRefresh={() => loadRenderJobs(1)}
              onDelete={handleDeleteJob}
              onDownload={(jobId, path) => handleDownload(jobId, path)}
              onViewDetails={handleViewJobDetails}
              hasMore={jobsHasMore}
              onLoadMore={() => loadRenderJobs(jobsPage + 1)}
            />
          )}

          {currentView === 'gallery' && (
            <Gallery
              key="gallery"
              projects={galleryProjects}
              onDelete={(id) => handleDeleteJob(id)}
              onDownload={() => handleDownload()}
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
