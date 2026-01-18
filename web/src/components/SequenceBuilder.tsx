import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  DndContext,
  closestCenter,
  KeyboardSensor,
  PointerSensor,
  useSensor,
  useSensors,
  type DragEndEvent,
} from '@dnd-kit/core';
import {
  arrayMove,
  SortableContext,
  sortableKeyboardCoordinates,
  verticalListSortingStrategy,
} from '@dnd-kit/sortable';
import { Plus, Users, ArrowRight, Wand2 } from 'lucide-react';
import { SubjectCard } from './SubjectCard';
import type { Subject } from '../types';

interface SequenceBuilderProps {
  subjects: Subject[];
  onSubjectsChange: (subjects: Subject[]) => void;
  onContinue: () => void;
}

export function SequenceBuilder({ subjects, onSubjectsChange, onContinue }: SequenceBuilderProps) {
  const [isAddingNew, setIsAddingNew] = useState(false);
  const [editingSubject, setEditingSubject] = useState<Subject | null>(null);
  const [newName, setNewName] = useState('');
  const [newPrompt, setNewPrompt] = useState('');

  const sensors = useSensors(
    useSensor(PointerSensor),
    useSensor(KeyboardSensor, {
      coordinateGetter: sortableKeyboardCoordinates,
    })
  );

  const handleDragEnd = (event: DragEndEvent) => {
    const { active, over } = event;
    if (over && active.id !== over.id) {
      const oldIndex = subjects.findIndex((s) => s.id === active.id);
      const newIndex = subjects.findIndex((s) => s.id === over.id);
      onSubjectsChange(arrayMove(subjects, oldIndex, newIndex));
    }
  };

  const addSubject = () => {
    if (!newName.trim() || !newPrompt.trim()) return;
    
    const newSubject: Subject = {
      id: `subject_${Date.now()}`,
      name: newName.trim(),
      visual_prompt: newPrompt.trim(),
      status: 'pending',
    };
    
    onSubjectsChange([...subjects, newSubject]);
    setNewName('');
    setNewPrompt('');
    setIsAddingNew(false);
  };

  const updateSubject = () => {
    if (!editingSubject || !newName.trim() || !newPrompt.trim()) return;
    
    onSubjectsChange(
      subjects.map((s) =>
        s.id === editingSubject.id
          ? { ...s, name: newName.trim(), visual_prompt: newPrompt.trim() }
          : s
      )
    );
    setEditingSubject(null);
    setNewName('');
    setNewPrompt('');
  };

  const removeSubject = (id: string) => {
    onSubjectsChange(subjects.filter((s) => s.id !== id));
  };

  const handleEdit = (subject: Subject) => {
    setEditingSubject(subject);
    setNewName(subject.name);
    setNewPrompt(subject.visual_prompt);
    setIsAddingNew(false);
  };

  const cancelEdit = () => {
    setEditingSubject(null);
    setIsAddingNew(false);
    setNewName('');
    setNewPrompt('');
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-aurora-start to-aurora-mid flex items-center justify-center">
            <Users size={20} className="text-white" />
          </div>
          <div>
            <h2 className="text-xl font-bold text-snow">Build Your Sequence</h2>
            <p className="text-sm text-mist">Drag to reorder. The first subject is your anchor.</p>
          </div>
        </div>
        <div className="flex items-center gap-2 text-sm text-silver">
          <span className="font-mono bg-smoke/50 px-2 py-1 rounded">{subjects.length}</span>
          <span>subjects</span>
        </div>
      </div>

      {/* Sequence List */}
      <div className="glass-card p-6">
        <DndContext
          sensors={sensors}
          collisionDetection={closestCenter}
          onDragEnd={handleDragEnd}
        >
          <SortableContext
            items={subjects.map((s) => s.id)}
            strategy={verticalListSortingStrategy}
          >
            <div className="space-y-3">
              <AnimatePresence>
                {subjects.map((subject, index) => (
                  <SubjectCard
                    key={subject.id}
                    subject={subject}
                    index={index + 1}
                    onRemove={removeSubject}
                    onEdit={handleEdit}
                    isAnchor={index === 0}
                  />
                ))}
              </AnimatePresence>
            </div>
          </SortableContext>
        </DndContext>

        {/* Add/Edit Form */}
        <AnimatePresence>
          {(isAddingNew || editingSubject) && (
            <motion.div
              initial={{ opacity: 0, height: 0 }}
              animate={{ opacity: 1, height: 'auto' }}
              exit={{ opacity: 0, height: 0 }}
              className="mt-4 pt-4 border-t border-smoke"
            >
              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-silver mb-2">
                    Name
                  </label>
                  <input
                    type="text"
                    value={newName}
                    onChange={(e) => setNewName(e.target.value)}
                    placeholder="e.g., Elon Musk, Taylor Swift..."
                    className="input-field"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-silver mb-2">
                    Visual Description
                  </label>
                  <textarea
                    value={newPrompt}
                    onChange={(e) => setNewPrompt(e.target.value)}
                    placeholder="Describe their appearance, expression, outfit..."
                    rows={3}
                    className="input-field resize-none"
                  />
                </div>
                <div className="flex items-center gap-3">
                  <button
                    onClick={editingSubject ? updateSubject : addSubject}
                    disabled={!newName.trim() || !newPrompt.trim()}
                    className="btn-glow disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    <span className="flex items-center gap-2">
                      <Wand2 size={16} />
                      {editingSubject ? 'Update Subject' : 'Add Subject'}
                    </span>
                  </button>
                  <button onClick={cancelEdit} className="btn-ghost">
                    Cancel
                  </button>
                </div>
              </div>
            </motion.div>
          )}
        </AnimatePresence>

        {/* Add Button */}
        {!isAddingNew && !editingSubject && (
          <motion.button
            onClick={() => setIsAddingNew(true)}
            className="mt-4 w-full p-4 rounded-xl border-2 border-dashed border-smoke hover:border-aurora-start/50 flex items-center justify-center gap-2 text-mist hover:text-aurora-start transition-all duration-300 group"
            whileHover={{ scale: 1.01 }}
            whileTap={{ scale: 0.99 }}
          >
            <Plus size={20} className="group-hover:rotate-90 transition-transform duration-300" />
            <span className="font-medium">Add Subject</span>
          </motion.button>
        )}
      </div>

      {/* Continue Button */}
      {subjects.length >= 2 && (
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="flex justify-end"
        >
          <button onClick={onContinue} className="btn-glow flex items-center gap-2">
            Continue to Settings
            <ArrowRight size={18} />
          </button>
        </motion.div>
      )}
    </div>
  );
}
