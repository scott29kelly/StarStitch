import { useState } from 'react';
import { motion } from 'framer-motion';
import { 
  Settings, 
  MapPin, 
  Palette, 
  Clock, 
  Cpu, 
  Sparkles,
  ChevronDown,
  ArrowLeft,
  ArrowRight,
  Check
} from 'lucide-react';
import { SequenceBuilder } from './SequenceBuilder';
import type { ProjectConfig } from '../types';

interface ConfigurePanelProps {
  config: ProjectConfig;
  onConfigChange: (config: ProjectConfig) => void;
  onStartRender: () => void;
}

const aspectRatios = [
  { value: '9:16', label: 'Portrait', desc: 'TikTok / Reels' },
  { value: '16:9', label: 'Landscape', desc: 'YouTube / TV' },
  { value: '1:1', label: 'Square', desc: 'Instagram Feed' },
] as const;

const imageModels = [
  { value: 'black-forest-labs/flux-1.1-pro', label: 'Flux 1.1 Pro', desc: 'Best quality' },
  { value: 'black-forest-labs/flux-schnell', label: 'Flux Schnell', desc: 'Fast' },
];

const videoModels = [
  { value: 'fal-ai/kling-video/v1.6/pro/image-to-video', label: 'Kling v1.6 Pro', desc: 'Best morphing' },
  { value: 'fal-ai/kling-video/v1.5/standard', label: 'Kling v1.5', desc: 'Faster' },
];

export function ConfigurePanel({ config, onConfigChange, onStartRender }: ConfigurePanelProps) {
  const [step, setStep] = useState<'sequence' | 'scene' | 'settings' | 'review'>('sequence');
  const [activeDropdown, setActiveDropdown] = useState<string | null>(null);

  const updateConfig = <K extends keyof ProjectConfig>(key: K, value: ProjectConfig[K]) => {
    onConfigChange({ ...config, [key]: value });
  };

  const updateSettings = <K extends keyof ProjectConfig['settings']>(
    key: K, 
    value: ProjectConfig['settings'][K]
  ) => {
    onConfigChange({
      ...config,
      settings: { ...config.settings, [key]: value },
    });
  };

  const updateScene = <K extends keyof ProjectConfig['global_scene']>(
    key: K, 
    value: ProjectConfig['global_scene'][K]
  ) => {
    onConfigChange({
      ...config,
      global_scene: { ...config.global_scene, [key]: value },
    });
  };

  const steps = [
    { id: 'sequence', label: 'Subjects', icon: <Sparkles size={16} /> },
    { id: 'scene', label: 'Scene', icon: <MapPin size={16} /> },
    { id: 'settings', label: 'Settings', icon: <Settings size={16} /> },
    { id: 'review', label: 'Review', icon: <Check size={16} /> },
  ] as const;

  const currentStepIndex = steps.findIndex(s => s.id === step);

  return (
    <div className="max-w-4xl mx-auto">
      {/* Step Indicator */}
      <div className="glass-card p-4 mb-8">
        <div className="flex items-center justify-between">
          {steps.map((s, index) => (
            <div key={s.id} className="flex items-center">
              <button
                onClick={() => setStep(s.id)}
                className={`
                  flex items-center gap-2 px-4 py-2 rounded-lg transition-all duration-300
                  ${step === s.id 
                    ? 'bg-aurora-start/20 text-aurora-start' 
                    : index < currentStepIndex
                      ? 'text-success hover:bg-smoke/50'
                      : 'text-mist hover:bg-smoke/50'
                  }
                `}
              >
                <span className={`
                  w-6 h-6 rounded-full flex items-center justify-center text-xs font-bold
                  ${step === s.id 
                    ? 'bg-aurora-start text-white' 
                    : index < currentStepIndex
                      ? 'bg-success text-white'
                      : 'bg-smoke text-mist'
                  }
                `}>
                  {index < currentStepIndex ? <Check size={12} /> : index + 1}
                </span>
                <span className="font-medium hidden sm:inline">{s.label}</span>
              </button>
              {index < steps.length - 1 && (
                <div className={`
                  w-12 h-0.5 mx-2
                  ${index < currentStepIndex ? 'bg-success' : 'bg-smoke'}
                `} />
              )}
            </div>
          ))}
        </div>
      </div>

      {/* Step Content */}
      <motion.div
        key={step}
        initial={{ opacity: 0, x: 20 }}
        animate={{ opacity: 1, x: 0 }}
        exit={{ opacity: 0, x: -20 }}
        transition={{ duration: 0.3 }}
      >
        {step === 'sequence' && (
          <SequenceBuilder
            subjects={config.sequence}
            onSubjectsChange={(subjects) => updateConfig('sequence', subjects)}
            onContinue={() => setStep('scene')}
          />
        )}

        {step === 'scene' && (
          <div className="space-y-6">
            <div className="flex items-center gap-3 mb-6">
              <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-neon-cyan to-neon-emerald flex items-center justify-center">
                <MapPin size={20} className="text-white" />
              </div>
              <div>
                <h2 className="text-xl font-bold text-snow">Set the Scene</h2>
                <p className="text-sm text-mist">Where are your subjects taking their selfies?</p>
              </div>
            </div>

            <div className="glass-card p-6 space-y-6">
              <div>
                <label className="block text-sm font-medium text-silver mb-2">
                  Project Name
                </label>
                <input
                  type="text"
                  value={config.project_name}
                  onChange={(e) => updateConfig('project_name', e.target.value)}
                  placeholder="my_awesome_stitch"
                  className="input-field font-mono"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-silver mb-2">
                  Location & Mood
                </label>
                <textarea
                  value={config.global_scene.location_prompt}
                  onChange={(e) => updateScene('location_prompt', e.target.value)}
                  placeholder="taking a selfie at the Eiffel Tower, golden hour lighting, 4k photorealistic..."
                  rows={4}
                  className="input-field resize-none"
                />
                <p className="text-xs text-mist mt-2">
                  This prompt will be combined with each subject's description.
                </p>
              </div>

              <div>
                <label className="block text-sm font-medium text-silver mb-2">
                  Negative Prompt (avoid these)
                </label>
                <input
                  type="text"
                  value={config.global_scene.negative_prompt}
                  onChange={(e) => updateScene('negative_prompt', e.target.value)}
                  placeholder="blurry, distorted, cartoon, low quality..."
                  className="input-field"
                />
              </div>
            </div>

            <div className="flex items-center justify-between">
              <button onClick={() => setStep('sequence')} className="btn-ghost flex items-center gap-2">
                <ArrowLeft size={18} />
                Back
              </button>
              <button onClick={() => setStep('settings')} className="btn-glow flex items-center gap-2">
                Continue
                <ArrowRight size={18} />
              </button>
            </div>
          </div>
        )}

        {step === 'settings' && (
          <div className="space-y-6">
            <div className="flex items-center gap-3 mb-6">
              <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-aurora-mid to-aurora-end flex items-center justify-center">
                <Settings size={20} className="text-white" />
              </div>
              <div>
                <h2 className="text-xl font-bold text-snow">Fine-tune Settings</h2>
                <p className="text-sm text-mist">Adjust quality, duration, and AI models.</p>
              </div>
            </div>

            <div className="glass-card p-6 space-y-8">
              {/* Aspect Ratio */}
              <div>
                <label className="block text-sm font-medium text-silver mb-3">
                  <Palette size={16} className="inline mr-2" />
                  Aspect Ratio
                </label>
                <div className="grid grid-cols-3 gap-3">
                  {aspectRatios.map((ar) => (
                    <button
                      key={ar.value}
                      onClick={() => updateSettings('aspect_ratio', ar.value)}
                      className={`
                        p-4 rounded-xl border-2 transition-all duration-300 text-left
                        ${config.settings.aspect_ratio === ar.value
                          ? 'border-aurora-start bg-aurora-start/10'
                          : 'border-smoke hover:border-mist'
                        }
                      `}
                    >
                      <div className="flex items-center gap-3">
                        <div className={`
                          ${ar.value === '9:16' ? 'w-6 h-10' : ar.value === '16:9' ? 'w-10 h-6' : 'w-8 h-8'}
                          border-2 rounded
                          ${config.settings.aspect_ratio === ar.value ? 'border-aurora-start' : 'border-mist'}
                        `} />
                        <div>
                          <p className="font-medium text-snow">{ar.label}</p>
                          <p className="text-xs text-mist">{ar.desc}</p>
                        </div>
                      </div>
                    </button>
                  ))}
                </div>
              </div>

              {/* Duration */}
              <div>
                <label className="block text-sm font-medium text-silver mb-3">
                  <Clock size={16} className="inline mr-2" />
                  Transition Duration: {config.settings.transition_duration_sec}s
                </label>
                <input
                  type="range"
                  min={3}
                  max={10}
                  value={config.settings.transition_duration_sec}
                  onChange={(e) => updateSettings('transition_duration_sec', parseInt(e.target.value))}
                  className="w-full h-2 bg-smoke rounded-full appearance-none cursor-pointer
                    [&::-webkit-slider-thumb]:appearance-none
                    [&::-webkit-slider-thumb]:w-5
                    [&::-webkit-slider-thumb]:h-5
                    [&::-webkit-slider-thumb]:rounded-full
                    [&::-webkit-slider-thumb]:bg-aurora-start
                    [&::-webkit-slider-thumb]:shadow-glow
                    [&::-webkit-slider-thumb]:cursor-pointer
                  "
                />
                <div className="flex justify-between text-xs text-mist mt-2">
                  <span>3s (fast)</span>
                  <span>10s (smooth)</span>
                </div>
              </div>

              {/* Model Selectors */}
              <div className="grid grid-cols-2 gap-4">
                {/* Image Model */}
                <div className="relative">
                  <label className="block text-sm font-medium text-silver mb-2">
                    <Cpu size={14} className="inline mr-2" />
                    Image Model
                  </label>
                  <button
                    onClick={() => setActiveDropdown(activeDropdown === 'image' ? null : 'image')}
                    className="input-field flex items-center justify-between"
                  >
                    <span className="truncate">
                      {imageModels.find(m => m.value === config.settings.image_model)?.label || 'Select...'}
                    </span>
                    <ChevronDown size={16} className={`transition-transform ${activeDropdown === 'image' ? 'rotate-180' : ''}`} />
                  </button>
                  {activeDropdown === 'image' && (
                    <motion.div
                      initial={{ opacity: 0, y: -10 }}
                      animate={{ opacity: 1, y: 0 }}
                      className="absolute z-50 w-full mt-2 glass-card p-2"
                    >
                      {imageModels.map((model) => (
                        <button
                          key={model.value}
                          onClick={() => {
                            updateSettings('image_model', model.value);
                            setActiveDropdown(null);
                          }}
                          className="w-full p-3 rounded-lg hover:bg-smoke/50 text-left transition-colors"
                        >
                          <p className="font-medium text-snow">{model.label}</p>
                          <p className="text-xs text-mist">{model.desc}</p>
                        </button>
                      ))}
                    </motion.div>
                  )}
                </div>

                {/* Video Model */}
                <div className="relative">
                  <label className="block text-sm font-medium text-silver mb-2">
                    <Cpu size={14} className="inline mr-2" />
                    Video Model
                  </label>
                  <button
                    onClick={() => setActiveDropdown(activeDropdown === 'video' ? null : 'video')}
                    className="input-field flex items-center justify-between"
                  >
                    <span className="truncate">
                      {videoModels.find(m => m.value === config.settings.video_model)?.label || 'Select...'}
                    </span>
                    <ChevronDown size={16} className={`transition-transform ${activeDropdown === 'video' ? 'rotate-180' : ''}`} />
                  </button>
                  {activeDropdown === 'video' && (
                    <motion.div
                      initial={{ opacity: 0, y: -10 }}
                      animate={{ opacity: 1, y: 0 }}
                      className="absolute z-50 w-full mt-2 glass-card p-2"
                    >
                      {videoModels.map((model) => (
                        <button
                          key={model.value}
                          onClick={() => {
                            updateSettings('video_model', model.value);
                            setActiveDropdown(null);
                          }}
                          className="w-full p-3 rounded-lg hover:bg-smoke/50 text-left transition-colors"
                        >
                          <p className="font-medium text-snow">{model.label}</p>
                          <p className="text-xs text-mist">{model.desc}</p>
                        </button>
                      ))}
                    </motion.div>
                  )}
                </div>
              </div>
            </div>

            <div className="flex items-center justify-between">
              <button onClick={() => setStep('scene')} className="btn-ghost flex items-center gap-2">
                <ArrowLeft size={18} />
                Back
              </button>
              <button onClick={() => setStep('review')} className="btn-glow flex items-center gap-2">
                Review & Generate
                <ArrowRight size={18} />
              </button>
            </div>
          </div>
        )}

        {step === 'review' && (
          <div className="space-y-6">
            <div className="flex items-center gap-3 mb-6">
              <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-success to-neon-emerald flex items-center justify-center">
                <Check size={20} className="text-white" />
              </div>
              <div>
                <h2 className="text-xl font-bold text-snow">Ready to Generate</h2>
                <p className="text-sm text-mist">Review your configuration and start the magic.</p>
              </div>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div className="glass-card p-6">
                <h3 className="text-sm font-semibold text-silver uppercase tracking-wider mb-4">Project</h3>
                <p className="text-2xl font-bold text-snow font-mono">{config.project_name}</p>
                <p className="text-mist mt-2">{config.global_scene.location_prompt.slice(0, 50)}...</p>
              </div>
              
              <div className="glass-card p-6">
                <h3 className="text-sm font-semibold text-silver uppercase tracking-wider mb-4">Sequence</h3>
                <p className="text-2xl font-bold text-aurora">
                  {config.sequence.length} subjects
                </p>
                <p className="text-mist mt-2">{config.sequence.length - 1} morphing transitions</p>
              </div>

              <div className="glass-card p-6">
                <h3 className="text-sm font-semibold text-silver uppercase tracking-wider mb-4">Output</h3>
                <p className="text-2xl font-bold text-snow">{config.settings.aspect_ratio}</p>
                <p className="text-mist mt-2">{config.settings.transition_duration_sec}s per transition</p>
              </div>

              <div className="glass-card p-6">
                <h3 className="text-sm font-semibold text-silver uppercase tracking-wider mb-4">Estimated</h3>
                <p className="text-2xl font-bold text-warning">
                  ~{(config.sequence.length - 1) * config.settings.transition_duration_sec}s
                </p>
                <p className="text-mist mt-2">final video length</p>
              </div>
            </div>

            <div className="glass-card p-6">
              <h3 className="text-sm font-semibold text-silver uppercase tracking-wider mb-4">Subjects Preview</h3>
              <div className="flex flex-wrap gap-2">
                {config.sequence.map((subject, index) => (
                  <div key={subject.id} className="flex items-center gap-2 bg-smoke/50 px-3 py-2 rounded-lg">
                    <span className="w-5 h-5 rounded bg-aurora-start/30 text-xs flex items-center justify-center text-aurora-start font-bold">
                      {index + 1}
                    </span>
                    <span className="text-cloud text-sm">{subject.name}</span>
                  </div>
                ))}
              </div>
            </div>

            <div className="flex items-center justify-between">
              <button onClick={() => setStep('settings')} className="btn-ghost flex items-center gap-2">
                <ArrowLeft size={18} />
                Back
              </button>
              <motion.button
                onClick={onStartRender}
                className="btn-glow flex items-center gap-3 px-8 py-4 text-lg"
                whileHover={{ scale: 1.02 }}
                whileTap={{ scale: 0.98 }}
              >
                <Sparkles size={22} />
                Start Generation
              </motion.button>
            </div>
          </div>
        )}
      </motion.div>
    </div>
  );
}
