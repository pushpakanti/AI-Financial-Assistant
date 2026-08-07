import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { apiService } from '../services/apiService';
import { Card, CardContent } from '../components/ui/Card';
import { Button } from '../components/ui/Button';
import { Input } from '../components/ui/Input';
import { Modal } from '../components/ui/Modal';
import { Badge } from '../components/ui/Badge';
import { useToast } from '../contexts/ToastContext';
import {
  Target,
  Plus,
  Trash2,
  Edit2,
  Calendar,
  Loader2,
  BrainCircuit,
  Lightbulb
} from 'lucide-react';
import type { GoalProgress } from '../types';

export const Goals: React.FC = () => {
  const queryClient = useQueryClient();
  const toast = useToast();

  const [isAddOpen, setIsAddOpen] = useState(false);
  const [isEditOpen, setIsEditOpen] = useState(false);
  const [selectedGoal, setSelectedGoal] = useState<GoalProgress | null>(null);

  // Form states
  const [formTitle, setFormTitle] = useState('');
  const [formTargetAmount, setFormTargetAmount] = useState<number>(0);
  const [formCurrentAmount, setFormCurrentAmount] = useState<number>(0);
  const [formDeadline, setFormDeadline] = useState<string>(new Date().toISOString().split('T')[0]);
  const [formPriority, setFormPriority] = useState('MEDIUM');

  // Query Goal Progress (contains basic Goal details + calculated progress fields)
  const { data: goals = [], isLoading } = useQuery({
    queryKey: ['goalsProgress'],
    queryFn: apiService.getGoalProgress,
  });

  // Query Goal Summary metrics
  const { data: summary } = useQuery({
    queryKey: ['goalsSummary'],
    queryFn: apiService.getGoalSummary,
  });

  // Query predictions
  const { data: predictions = [] } = useQuery({
    queryKey: ['goalsPredictions'],
    queryFn: apiService.getGoalPredictions,
  });

  // Query recommendations
  const { data: recommendations = [] } = useQuery({
    queryKey: ['goalsRecommendations'],
    queryFn: apiService.getGoalRecommendations,
  });

  // Create Goal
  const createMutation = useMutation({
    mutationFn: apiService.createGoal,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['goalsProgress'] });
      queryClient.invalidateQueries({ queryKey: ['goalsSummary'] });
      queryClient.invalidateQueries({ queryKey: ['goalsPredictions'] });
      queryClient.invalidateQueries({ queryKey: ['goalsRecommendations'] });
      queryClient.invalidateQueries({ queryKey: ['dashboard'] });
      toast.showToast('Financial goal set successfully', 'success');
      setIsAddOpen(false);
      resetForm();
    },
    onError: (err: any) => {
      toast.showToast(err.message || 'Failed to create goal', 'error');
    },
  });

  // Update Goal
  const updateMutation = useMutation({
    mutationFn: ({ id, data }: { id: number; data: any }) => apiService.updateGoal(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['goalsProgress'] });
      queryClient.invalidateQueries({ queryKey: ['goalsSummary'] });
      queryClient.invalidateQueries({ queryKey: ['goalsPredictions'] });
      queryClient.invalidateQueries({ queryKey: ['goalsRecommendations'] });
      queryClient.invalidateQueries({ queryKey: ['dashboard'] });
      toast.showToast('Goal updated successfully', 'success');
      setIsEditOpen(false);
      setSelectedGoal(null);
      resetForm();
    },
    onError: (err: any) => {
      toast.showToast(err.message || 'Failed to update goal', 'error');
    },
  });

  // Delete Goal
  const deleteMutation = useMutation({
    mutationFn: apiService.deleteGoal,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['goalsProgress'] });
      queryClient.invalidateQueries({ queryKey: ['goalsSummary'] });
      queryClient.invalidateQueries({ queryKey: ['goalsPredictions'] });
      queryClient.invalidateQueries({ queryKey: ['goalsRecommendations'] });
      queryClient.invalidateQueries({ queryKey: ['dashboard'] });
      toast.showToast('Goal deleted successfully', 'success');
    },
    onError: (err: any) => {
      toast.showToast(err.message || 'Failed to delete goal', 'error');
    },
  });

  const resetForm = () => {
    setFormTitle('');
    setFormTargetAmount(0);
    setFormCurrentAmount(0);
    setFormDeadline(new Date().toISOString().split('T')[0]);
    setFormPriority('MEDIUM');
  };

  const handleCreateSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!formTitle.trim()) {
      toast.showToast('Goal title cannot be blank', 'info');
      return;
    }
    if (formTargetAmount <= 0) {
      toast.showToast('Target amount must be positive', 'info');
      return;
    }

    createMutation.mutate({
      title: formTitle,
      target_amount: formTargetAmount,
      current_amount: formCurrentAmount,
      deadline: formDeadline,
      priority: formPriority,
    });
  };

  const handleEditSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedGoal) return;
    if (!formTitle.trim()) {
      toast.showToast('Goal title cannot be blank', 'info');
      return;
    }
    if (formTargetAmount <= 0) {
      toast.showToast('Target amount must be positive', 'info');
      return;
    }

    updateMutation.mutate({
      id: selectedGoal.id,
      data: {
        title: formTitle,
        target_amount: formTargetAmount,
        current_amount: formCurrentAmount,
        deadline: formDeadline,
        priority: formPriority,
      },
    });
  };

  const handleEditOpen = (goal: GoalProgress) => {
    setSelectedGoal(goal);
    setFormTitle(goal.title);
    setFormTargetAmount(goal.target_amount);
    setFormCurrentAmount(goal.current_amount);
    setFormDeadline(goal.deadline.split('T')[0]);
    setFormPriority(goal.priority);
    setIsEditOpen(true);
  };

  const handleDelete = (id: number) => {
    if (window.confirm('Delete this goal record?')) {
      deleteMutation.mutate(id);
    }
  };

  return (
    <div className="flex flex-col gap-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h2 className="text-xl md:text-2xl font-extrabold text-slate-850 dark:text-slate-100 tracking-tight">
            Financial Goals
          </h2>
          <p className="text-sm text-slate-500 dark:text-slate-400 mt-1">
            Establish financial objectives, predict your target dates, and review AI recommendations.
          </p>
        </div>
        <Button onClick={() => { resetForm(); setIsAddOpen(true); }} leftIcon={<Plus className="w-4 h-4" />}>
          New Goal
        </Button>
      </div>

      {/* Summary Cards */}
      {summary && (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5">
          <Card>
            <CardContent className="flex flex-col text-left">
              <span className="text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider">
                Total Goal Assets
              </span>
              <span className="text-2xl font-black text-slate-850 dark:text-slate-100 mt-1">
                ₹{summary.total_current_amount}
              </span>
              <span className="text-[10px] text-slate-400 mt-1.5 font-medium">
                Saved towards ₹{summary.total_target_amount} aggregate target
              </span>
            </CardContent>
          </Card>

          <Card>
            <CardContent className="flex flex-col text-left">
              <span className="text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider">
                Remaining Debt
              </span>
              <span className="text-2xl font-black text-slate-850 dark:text-slate-100 mt-1 text-indigo-650">
                ₹{summary.total_remaining_amount}
              </span>
              <span className="text-[10px] text-slate-400 mt-1.5 font-medium">
                Aggregate deficit remaining
              </span>
            </CardContent>
          </Card>

          <Card>
            <CardContent className="flex flex-col text-left">
              <span className="text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider">
                Savings Ratio
              </span>
              <span className="text-2xl font-black text-slate-850 dark:text-slate-100 mt-1 text-emerald-600">
                {Math.round(summary.overall_completion_percentage)}%
              </span>
              <span className="text-[10px] text-slate-400 mt-1.5 font-medium">
                Overall milestone achievement
              </span>
            </CardContent>
          </Card>

          <Card>
            <CardContent className="flex flex-col text-left">
              <span className="text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider">
                Active Targets
              </span>
              <span className="text-2xl font-black text-slate-850 dark:text-slate-100 mt-1">
                {summary.active_goals} <span className="text-slate-400 text-sm">/ {summary.total_goals}</span>
              </span>
              <span className="text-[10px] text-slate-400 mt-1.5 font-medium">
                {summary.completed_goals} goals completed successfully
              </span>
            </CardContent>
          </Card>
        </div>
      )}

      {/* Goals List */}
      {isLoading ? (
        <div className="flex flex-col items-center justify-center min-h-[30vh] gap-3">
          <Loader2 className="w-8 h-8 animate-spin text-indigo-650" />
          <span className="text-xs text-slate-500 font-medium">Fetching goals tracker...</span>
        </div>
      ) : goals.length === 0 ? (
        <Card className="py-12 text-center max-w-md mx-auto mt-6">
          <CardContent className="flex flex-col items-center justify-center p-8">
            <Target className="w-12 h-12 text-slate-350 mb-3" />
            <h4 className="text-base font-bold text-slate-805 dark:text-slate-205">No Active Goals Set</h4>
            <p className="text-xs text-slate-500 mt-1 mb-6">Define key financial milestones to project completion timelines.</p>
            <Button onClick={() => { resetForm(); setIsAddOpen(true); }} leftIcon={<Plus className="w-4 h-4" />}>
              Configure First Goal
            </Button>
          </CardContent>
        </Card>
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {goals.map((goal) => {
            const pct = Math.min(100, Math.round(goal.percentage_complete));
            
            // Find prediction matching goal id
            const pred = predictions.find((p) => p.goal_id === goal.id);
            // Find recommendations matching goal id
            const rec = recommendations.find((r) => r.goal_id === goal.id);

            let priorityVariant: any = 'primary';
            if (goal.priority === 'HIGH') priorityVariant = 'danger';
            if (goal.priority === 'LOW') priorityVariant = 'secondary';

            return (
              <Card key={goal.id} className="hover:shadow-lg transition-all duration-200">
                <CardContent className="p-6 flex flex-col gap-4 text-left">
                  <div className="flex items-start justify-between gap-3">
                    <div className="flex flex-col">
                      <div className="flex items-center gap-2">
                        <span className="text-sm font-black text-slate-850 dark:text-slate-100">
                          {goal.title}
                        </span>
                        <Badge variant={priorityVariant} className="text-[9px] px-1.5 py-0">
                          {goal.priority}
                        </Badge>
                      </div>
                      <span className="text-[10px] text-slate-400 font-medium mt-1 flex items-center gap-1">
                        <Calendar className="w-3.5 h-3.5" /> Target Date: {new Date(goal.deadline).toLocaleDateString()}
                      </span>
                    </div>

                    <div className="flex items-center gap-1 shrink-0">
                      <button
                        onClick={() => handleEditOpen(goal)}
                        className="p-1.5 hover:bg-slate-100 dark:hover:bg-slate-800 rounded-lg text-slate-400 hover:text-indigo-650"
                        title="Edit Goal"
                      >
                        <Edit2 className="w-3.5 h-3.5" />
                      </button>
                      <button
                        onClick={() => handleDelete(goal.id)}
                        className="p-1.5 hover:bg-slate-100 dark:hover:bg-slate-800 rounded-lg text-slate-400 hover:text-rose-600"
                        title="Remove Goal"
                      >
                        <Trash2 className="w-3.5 h-3.5" />
                      </button>
                    </div>
                  </div>

                  {/* Progress Details */}
                  <div className="flex justify-between items-baseline mt-1">
                    <div>
                      <span className="text-2xl font-black text-slate-805 dark:text-slate-50">
                        ₹{goal.current_amount}
                      </span>
                      <span className="text-xs text-slate-400 ml-1 font-semibold">
                        saved of ₹{goal.target_amount}
                      </span>
                    </div>
                    <span className="text-xs font-black text-indigo-650 dark:text-indigo-400">
                      {pct}% saved
                    </span>
                  </div>

                  {/* Progress Bar */}
                  <div className="w-full h-2.5 rounded-full bg-slate-100 dark:bg-slate-800 overflow-hidden">
                    <div className="h-full rounded-full bg-indigo-600" style={{ width: `${pct}%` }} />
                  </div>

                  {/* Prediction panel (if exists) */}
                  {pred && (
                    <div className="p-3.5 bg-indigo-50/20 dark:bg-indigo-950/10 border border-indigo-150/30 dark:border-indigo-900/10 rounded-xl flex items-start gap-2.5">
                      <BrainCircuit className="w-4 h-4 text-indigo-600 shrink-0 mt-0.5" />
                      <div className="flex flex-col gap-0.5 text-xs text-slate-655 dark:text-slate-350">
                        <span className="font-bold text-[10px] uppercase text-indigo-600 tracking-wider">AI Target Predictions</span>
                        <p className="mt-0.5 leading-relaxed font-semibold">
                          {pred.projected_completion_date ? (
                            <>Projected completion: <span className="font-black text-slate-800 dark:text-slate-100">{new Date(pred.projected_completion_date).toLocaleDateString()}</span></>
                          ) : (
                            <span>{pred.prediction_basis}</span>
                          )}
                        </p>
                        <p className="text-[10px] text-slate-455 mt-0.5 font-semibold">
                          Required contribution: <span className="font-extrabold text-slate-700 dark:text-slate-200">₹{Math.round(pred.required_monthly_contribution)}/month</span>
                        </p>
                      </div>
                    </div>
                  )}

                  {/* Recommendation list (if exists) */}
                  {rec && rec.recommendations.length > 0 && (
                    <div className="p-3.5 bg-emerald-50/20 dark:bg-emerald-950/10 border border-emerald-150/30 dark:border-emerald-900/10 rounded-xl flex items-start gap-2.5">
                      <Lightbulb className="w-4 h-4 text-emerald-600 shrink-0 mt-0.5" />
                      <div className="flex flex-col gap-0.5 text-xs text-slate-655 dark:text-slate-350">
                        <span className="font-bold text-[10px] uppercase text-emerald-600 tracking-wider">AI Optimization Tips</span>
                        <ul className="list-disc pl-4 mt-1 flex flex-col gap-1 font-semibold text-[10.5px]">
                          {rec.recommendations.map((tip, idx) => (
                            <li key={idx} className="leading-relaxed">{tip}</li>
                          ))}
                        </ul>
                      </div>
                    </div>
                  )}
                </CardContent>
              </Card>
            );
          })}
        </div>
      )}

      {/* MODAL: ADD GOAL */}
      <Modal isOpen={isAddOpen} onClose={() => setIsAddOpen(false)} title="Create Financial Goal">
        <form onSubmit={handleCreateSubmit} className="flex flex-col gap-4">
          <Input
            label="Goal Objective"
            placeholder="e.g. Save for Down Payment"
            value={formTitle}
            onChange={(e) => setFormTitle(e.target.value)}
            required
          />

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <Input
              label="Target Amount (INR)"
              type="number"
              value={formTargetAmount || ''}
              onChange={(e) => setFormTargetAmount(Number(e.target.value))}
              required
            />

            <Input
              label="Current Progress Balance"
              type="number"
              value={formCurrentAmount || ''}
              onChange={(e) => setFormCurrentAmount(Number(e.target.value))}
            />
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <Input
              label="Deadline Target"
              type="date"
              value={formDeadline}
              onChange={(e) => setFormDeadline(e.target.value)}
              required
            />

            <div className="flex flex-col gap-1.5">
              <label className="text-xs font-semibold text-slate-655 dark:text-slate-400">Priority Level</label>
              <select
                value={formPriority}
                onChange={(e) => setFormPriority(e.target.value)}
                className="w-full px-3.5 py-2.5 rounded-xl border border-slate-350 dark:border-slate-800 bg-white/50 dark:bg-slate-900/50 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500/50"
              >
                <option value="LOW">Low Priority</option>
                <option value="MEDIUM">Medium Priority</option>
                <option value="HIGH">High Priority</option>
              </select>
            </div>
          </div>

          <div className="flex justify-end gap-2.5 mt-4">
            <Button type="button" variant="outline" onClick={() => setIsAddOpen(false)}>
              Cancel
            </Button>
            <Button type="submit" isLoading={createMutation.isPending}>
              Create Goal
            </Button>
          </div>
        </form>
      </Modal>

      {/* MODAL: EDIT GOAL */}
      <Modal isOpen={isEditOpen} onClose={() => setIsEditOpen(false)} title="Edit Goal Details">
        <form onSubmit={handleEditSubmit} className="flex flex-col gap-4">
          <Input
            label="Goal Objective"
            placeholder="e.g. Save for Down Payment"
            value={formTitle}
            onChange={(e) => setFormTitle(e.target.value)}
            required
          />

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <Input
              label="Target Amount (INR)"
              type="number"
              value={formTargetAmount || ''}
              onChange={(e) => setFormTargetAmount(Number(e.target.value))}
              required
            />

            <Input
              label="Current Progress Balance"
              type="number"
              value={formCurrentAmount || ''}
              onChange={(e) => setFormCurrentAmount(Number(e.target.value))}
            />
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <Input
              label="Deadline Target"
              type="date"
              value={formDeadline}
              onChange={(e) => setFormDeadline(e.target.value)}
              required
            />

            <div className="flex flex-col gap-1.5">
              <label className="text-xs font-semibold text-slate-655 dark:text-slate-400">Priority Level</label>
              <select
                value={formPriority}
                onChange={(e) => setFormPriority(e.target.value)}
                className="w-full px-3.5 py-2.5 rounded-xl border border-slate-350 dark:border-slate-800 bg-white/50 dark:bg-slate-900/50 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500/50"
              >
                <option value="LOW">Low Priority</option>
                <option value="MEDIUM">Medium Priority</option>
                <option value="HIGH">High Priority</option>
              </select>
            </div>
          </div>

          <div className="flex justify-end gap-2.5 mt-4">
            <Button type="button" variant="outline" onClick={() => setIsEditOpen(false)}>
              Cancel
            </Button>
            <Button type="submit" isLoading={updateMutation.isPending}>
              Save Changes
            </Button>
          </div>
        </form>
      </Modal>
    </div>
  );
};
export default Goals;
