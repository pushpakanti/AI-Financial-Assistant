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
  PiggyBank,
  Plus,
  Trash2,
  Edit2,
  AlertTriangle,
  Loader2,
  CheckCircle,
  Calendar
} from 'lucide-react';
import type { BudgetProgress } from '../types';

export const Budgets: React.FC = () => {
  const queryClient = useQueryClient();
  const toast = useToast();

  const [isAddOpen, setIsAddOpen] = useState(false);
  const [isEditOpen, setIsEditOpen] = useState(false);
  const [selectedBudget, setSelectedBudget] = useState<BudgetProgress | null>(null);

  // Form states
  const [formName, setFormName] = useState('');
  const [formCategory, setFormCategory] = useState<number | undefined>(undefined);
  const [formAmount, setFormAmount] = useState<number>(0);
  const [formStartDate, setFormStartDate] = useState<string>(new Date(new Date().getFullYear(), new Date().getMonth(), 1).toISOString().split('T')[0]);
  const [formEndDate, setFormEndDate] = useState<string>(new Date(new Date().getFullYear(), new Date().getMonth() + 1, 0).toISOString().split('T')[0]);
  const [formThreshold, setFormThreshold] = useState<number>(80);

  // Query Budget Progress
  const { data: budgets = [], isLoading } = useQuery({
    queryKey: ['budgetsProgress'],
    queryFn: apiService.getBudgetProgress,
  });

  // Query Budget Summary
  const { data: summary } = useQuery({
    queryKey: ['budgetsSummary'],
    queryFn: apiService.getBudgetSummary,
  });

  // Query Categories for dropdown list
  const { data: categories = [] } = useQuery({
    queryKey: ['categories'],
    queryFn: apiService.getCategories,
  });

  // Create budget mutation
  const createMutation = useMutation({
    mutationFn: apiService.createBudget,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['budgetsProgress'] });
      queryClient.invalidateQueries({ queryKey: ['budgetsSummary'] });
      queryClient.invalidateQueries({ queryKey: ['dashboard'] });
      toast.showToast('Budget limit created successfully', 'success');
      setIsAddOpen(false);
      resetForm();
    },
    onError: (err: any) => {
      toast.showToast(err.message || 'Failed to create budget', 'error');
    },
  });

  // Update budget mutation
  const updateMutation = useMutation({
    mutationFn: ({ id, data }: { id: number; data: any }) => apiService.updateBudget(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['budgetsProgress'] });
      queryClient.invalidateQueries({ queryKey: ['budgetsSummary'] });
      queryClient.invalidateQueries({ queryKey: ['dashboard'] });
      toast.showToast('Budget updated successfully', 'success');
      setIsEditOpen(false);
      setSelectedBudget(null);
      resetForm();
    },
    onError: (err: any) => {
      toast.showToast(err.message || 'Failed to update budget', 'error');
    },
  });

  // Delete budget mutation
  const deleteMutation = useMutation({
    mutationFn: apiService.deleteBudget,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['budgetsProgress'] });
      queryClient.invalidateQueries({ queryKey: ['budgetsSummary'] });
      queryClient.invalidateQueries({ queryKey: ['dashboard'] });
      toast.showToast('Budget deleted successfully', 'success');
    },
    onError: (err: any) => {
      toast.showToast(err.message || 'Failed to delete budget', 'error');
    },
  });

  const resetForm = () => {
    setFormName('');
    setFormCategory(undefined);
    setFormAmount(0);
    setFormStartDate(new Date(new Date().getFullYear(), new Date().getMonth(), 1).toISOString().split('T')[0]);
    setFormEndDate(new Date(new Date().getFullYear(), new Date().getMonth() + 1, 0).toISOString().split('T')[0]);
    setFormThreshold(80);
  };

  const handleCreateSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!formName.trim()) {
      toast.showToast('Please specify a budget name', 'info');
      return;
    }
    if (formAmount <= 0) {
      toast.showToast('Budget limit amount must be greater than zero', 'info');
      return;
    }

    createMutation.mutate({
      name: formName,
      category_id: formCategory || null,
      budget_type: 'MONTHLY',
      amount: formAmount,
      start_date: formStartDate,
      end_date: formEndDate,
      alert_percentage: formThreshold,
    });
  };

  const handleEditSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedBudget) return;
    if (!formName.trim()) {
      toast.showToast('Budget name cannot be empty', 'info');
      return;
    }
    if (formAmount <= 0) {
      toast.showToast('Limit amount must be greater than zero', 'info');
      return;
    }

    updateMutation.mutate({
      id: selectedBudget.id,
      data: {
        name: formName,
        category_id: formCategory || null,
        budget_type: 'MONTHLY',
        amount: formAmount,
        start_date: formStartDate,
        end_date: formEndDate,
        alert_percentage: formThreshold,
      },
    });
  };

  const handleEditOpen = (budget: BudgetProgress) => {
    setSelectedBudget(budget);
    setFormName(budget.name);
    setFormCategory(budget.category_id || undefined);
    setFormAmount(budget.amount);
    setFormStartDate(budget.start_date.split('T')[0]);
    setFormEndDate(budget.end_date.split('T')[0]);
    setFormThreshold(Math.round(budget.alert_percentage));
    setIsEditOpen(true);
  };

  const handleDelete = (id: number) => {
    if (window.confirm('Are you sure you want to remove this budget?')) {
      deleteMutation.mutate(id);
    }
  };

  return (
    <div className="flex flex-col gap-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h2 className="text-xl md:text-2xl font-extrabold text-slate-850 dark:text-slate-100 tracking-tight">
            Budgets Tracker
          </h2>
          <p className="text-sm text-slate-500 dark:text-slate-400 mt-1">
            Establish maximum spending limits per category and configure alert triggers.
          </p>
        </div>
        <Button onClick={() => { resetForm(); setIsAddOpen(true); }} leftIcon={<Plus className="w-4 h-4" />}>
          Create Budget
        </Button>
      </div>

      {/* Summary Cards */}
      {summary && (
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-5">
          <Card>
            <CardContent className="flex items-center justify-between">
              <div className="flex flex-col text-left">
                <span className="text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider">
                  Total Budgeted
                </span>
                <span className="text-2xl font-black text-slate-850 dark:text-slate-100 mt-1">
                  ₹{summary.total_budgeted}
                </span>
                <span className="text-[10px] text-slate-400 mt-1.5 font-medium">
                  Across {summary.active_budget_count} active categories
                </span>
              </div>
              <div className="p-3 bg-indigo-50 dark:bg-indigo-950/20 text-indigo-650 dark:text-indigo-400 rounded-xl">
                <PiggyBank className="w-6 h-6" />
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardContent className="flex items-center justify-between">
              <div className="flex flex-col text-left">
                <span className="text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider">
                  Total Spent
                </span>
                <span className="text-2xl font-black text-slate-850 dark:text-slate-100 mt-1 text-rose-600">
                  ₹{summary.total_spent}
                </span>
                <span className="text-[10px] text-slate-400 mt-1.5 font-medium flex items-center gap-1">
                  {summary.total_budgeted > 0
                    ? `${Math.round((summary.total_spent / summary.total_budgeted) * 100)}% of total cap`
                    : 'No limits set'}
                </span>
              </div>
              <div className="p-3 bg-rose-50 dark:bg-rose-950/20 text-rose-600 dark:text-rose-455 rounded-xl">
                <AlertTriangle className="w-6 h-6" />
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardContent className="flex items-center justify-between">
              <div className="flex flex-col text-left">
                <span className="text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider">
                  Remaining Room
                </span>
                <span className={`text-2xl font-black mt-1 ${summary.total_remaining < 0 ? 'text-rose-600' : 'text-emerald-600'}`}>
                  ₹{summary.total_remaining}
                </span>
                <span className="text-[10px] text-slate-400 mt-1.5 font-medium">
                  Available margin to spend
                </span>
              </div>
              <div className="p-3 bg-emerald-50 dark:bg-emerald-950/20 text-emerald-600 dark:text-emerald-450 rounded-xl">
                <CheckCircle className="w-6 h-6" />
              </div>
            </CardContent>
          </Card>
        </div>
      )}

      {/* Budgets Grid List */}
      {isLoading ? (
        <div className="flex flex-col items-center justify-center min-h-[30vh] gap-3">
          <Loader2 className="w-8 h-8 animate-spin text-indigo-650" />
          <span className="text-xs text-slate-500 font-medium">Loading budgets...</span>
        </div>
      ) : budgets.length === 0 ? (
        <Card className="py-12 text-center max-w-md mx-auto mt-6">
          <CardContent className="flex flex-col items-center justify-center p-8">
            <PiggyBank className="w-12 h-12 text-slate-350 mb-3" />
            <h4 className="text-base font-bold text-slate-805 dark:text-slate-205">No Budgets Formulated</h4>
            <p className="text-xs text-slate-500 mt-1 mb-6">Create a category budget to control your daily spending habits.</p>
            <Button onClick={() => { resetForm(); setIsAddOpen(true); }} leftIcon={<Plus className="w-4 h-4" />}>
              Configure First Budget
            </Button>
          </CardContent>
        </Card>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {budgets.map((budget) => {
            const percent = Math.min(100, Math.round(budget.percentage_used));
            const isWarning = budget.status === 'warned';
            const isExceeded = budget.status === 'exceeded';

            let strokeColor = 'border-slate-200 dark:border-slate-800';
            let barColor = 'bg-indigo-600';
            let badgeVariant: any = 'primary';

            if (isExceeded) {
              strokeColor = 'border-rose-300 dark:border-rose-950/40';
              barColor = 'bg-rose-500';
              badgeVariant = 'danger';
            } else if (isWarning) {
              strokeColor = 'border-amber-300 dark:border-amber-950/40';
              barColor = 'bg-amber-500';
              badgeVariant = 'warning';
            }

            return (
              <Card key={budget.id} className={`border ${strokeColor} hover:shadow-lg transition-all duration-200`}>
                <CardContent className="p-6 flex flex-col gap-4">
                  <div className="flex items-start justify-between gap-3">
                    <div className="flex flex-col text-left">
                      <div className="flex items-center gap-2">
                        <span className="text-sm font-black text-slate-800 dark:text-slate-100">
                          {budget.name}
                        </span>
                        {budget.category_id && (
                          <span className="text-[10px] bg-slate-100 dark:bg-slate-800 text-slate-500 dark:text-slate-400 font-semibold px-2 py-0.5 rounded-full">
                            Category Limit
                          </span>
                        )}
                      </div>
                      <span className="text-[10px] text-slate-400 font-medium mt-1">
                        Validity: {new Date(budget.start_date).toLocaleDateString()} - {new Date(budget.end_date).toLocaleDateString()}
                      </span>
                    </div>

                    <div className="flex items-center gap-1">
                      <button
                        onClick={() => handleEditOpen(budget)}
                        className="p-1.5 hover:bg-slate-100 dark:hover:bg-slate-800 rounded-lg text-slate-400 hover:text-indigo-650"
                        title="Edit Budget"
                      >
                        <Edit2 className="w-3.5 h-3.5" />
                      </button>
                      <button
                        onClick={() => handleDelete(budget.id)}
                        className="p-1.5 hover:bg-slate-100 dark:hover:bg-slate-800 rounded-lg text-slate-400 hover:text-rose-650"
                        title="Remove Budget"
                      >
                        <Trash2 className="w-3.5 h-3.5" />
                      </button>
                    </div>
                  </div>

                  {/* Progress Details */}
                  <div className="flex justify-between items-baseline text-left mt-1">
                    <div>
                      <span className="text-2xl font-black text-slate-805 dark:text-slate-55">
                        ₹{budget.spent}
                      </span>
                      <span className="text-xs text-slate-400 ml-1 font-semibold">
                        spent of ₹{budget.amount}
                      </span>
                    </div>
                    <Badge variant={badgeVariant} className="uppercase text-[9px] px-2 font-black">
                      {percent}% Used
                    </Badge>
                  </div>

                  {/* Progress Bar */}
                  <div className="w-full h-2.5 rounded-full bg-slate-100 dark:bg-slate-800 overflow-hidden mt-1">
                    <div className={`h-full rounded-full ${barColor}`} style={{ width: `${percent}%` }} />
                  </div>

                  {/* Threshold Indicators */}
                  <div className="flex justify-between items-center text-[10px] text-slate-450 dark:text-slate-500 font-semibold">
                    <span className="flex items-center gap-1">
                      <Calendar className="w-3.5 h-3.5" />
                      Alert trigger set at {Math.round(budget.alert_percentage)}%
                    </span>
                    {isExceeded ? (
                      <span className="text-rose-500 font-black flex items-center gap-0.5">
                        <AlertTriangle className="w-3.5 h-3.5" /> Overdraft by ₹{Math.abs(budget.remaining)}
                      </span>
                    ) : (
                      <span>₹{budget.remaining} remaining margin</span>
                    )}
                  </div>
                </CardContent>
              </Card>
            );
          })}
        </div>
      )}

      {/* MODAL: CREATE BUDGET */}
      <Modal isOpen={isAddOpen} onClose={() => setIsAddOpen(false)} title="Create Category Budget">
        <form onSubmit={handleCreateSubmit} className="flex flex-col gap-4">
          <Input
            label="Budget Title / Label"
            placeholder="e.g. Monthly Grocery Cap"
            value={formName}
            onChange={(e) => setFormName(e.target.value)}
            required
          />

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div className="flex flex-col gap-1.5">
              <label className="text-xs font-semibold text-slate-655 dark:text-slate-400">Target Category</label>
              <select
                value={formCategory || ''}
                onChange={(e) => setFormCategory(Number(e.target.value) || undefined)}
                className="w-full px-3.5 py-2.5 rounded-xl border border-slate-350 dark:border-slate-800 bg-white/50 dark:bg-slate-900/50 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500/50"
              >
                <option value="">Apply to all transactions (Overall cap)</option>
                {categories.map((c) => (
                  <option key={c.id} value={c.id}>{c.name}</option>
                ))}
              </select>
            </div>

            <Input
              label="Limit Cap (INR)"
              type="number"
              value={formAmount || ''}
              onChange={(e) => setFormAmount(Number(e.target.value))}
              required
            />
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <Input
              label="Start Date"
              type="date"
              value={formStartDate}
              onChange={(e) => setFormStartDate(e.target.value)}
              required
            />

            <Input
              label="End Date"
              type="date"
              value={formEndDate}
              onChange={(e) => setFormEndDate(e.target.value)}
              required
            />
          </div>

          <div className="flex flex-col gap-1.5">
            <label className="text-xs font-semibold text-slate-655 dark:text-slate-400 flex justify-between">
              <span>Alert Threshold Limit</span>
              <span className="text-indigo-650 dark:text-indigo-400 font-bold">{formThreshold}%</span>
            </label>
            <input
              type="range"
              min="50"
              max="100"
              step="5"
              value={formThreshold}
              onChange={(e) => setFormThreshold(Number(e.target.value))}
              className="w-full h-1 bg-slate-200 dark:bg-slate-800 rounded-lg appearance-none cursor-pointer accent-indigo-650"
            />
            <span className="text-[10px] text-slate-400 font-medium">Trigger an alert panel once spending hits this percentage.</span>
          </div>

          <div className="flex justify-end gap-2.5 mt-4">
            <Button type="button" variant="outline" onClick={() => setIsAddOpen(false)}>
              Cancel
            </Button>
            <Button type="submit" isLoading={createMutation.isPending}>
              Create Budget
            </Button>
          </div>
        </form>
      </Modal>

      {/* MODAL: EDIT BUDGET */}
      <Modal isOpen={isEditOpen} onClose={() => setIsEditOpen(false)} title="Edit Budget Details">
        <form onSubmit={handleEditSubmit} className="flex flex-col gap-4">
          <Input
            label="Budget Title / Label"
            placeholder="e.g. Monthly Grocery Cap"
            value={formName}
            onChange={(e) => setFormName(e.target.value)}
            required
          />

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div className="flex flex-col gap-1.5">
              <label className="text-xs font-semibold text-slate-655 dark:text-slate-400">Target Category</label>
              <select
                value={formCategory || ''}
                onChange={(e) => setFormCategory(Number(e.target.value) || undefined)}
                className="w-full px-3.5 py-2.5 rounded-xl border border-slate-350 dark:border-slate-800 bg-white/50 dark:bg-slate-900/50 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500/50"
              >
                <option value="">Apply to all transactions (Overall cap)</option>
                {categories.map((c) => (
                  <option key={c.id} value={c.id}>{c.name}</option>
                ))}
              </select>
            </div>

            <Input
              label="Limit Cap (INR)"
              type="number"
              value={formAmount || ''}
              onChange={(e) => setFormAmount(Number(e.target.value))}
              required
            />
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <Input
              label="Start Date"
              type="date"
              value={formStartDate}
              onChange={(e) => setFormStartDate(e.target.value)}
              required
            />

            <Input
              label="End Date"
              type="date"
              value={formEndDate}
              onChange={(e) => setFormEndDate(e.target.value)}
              required
            />
          </div>

          <div className="flex flex-col gap-1.5">
            <label className="text-xs font-semibold text-slate-655 dark:text-slate-400 flex justify-between">
              <span>Alert Threshold Limit</span>
              <span className="text-indigo-650 dark:text-indigo-400 font-bold">{formThreshold}%</span>
            </label>
            <input
              type="range"
              min="50"
              max="100"
              step="5"
              value={formThreshold}
              onChange={(e) => setFormThreshold(Number(e.target.value))}
              className="w-full h-1 bg-slate-200 dark:bg-slate-800 rounded-lg appearance-none cursor-pointer accent-indigo-650"
            />
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
export default Budgets;
