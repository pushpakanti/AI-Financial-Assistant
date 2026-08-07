import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { apiService } from '../services/apiService';
import { Card, CardContent } from '../components/ui/Card';
import { Button } from '../components/ui/Button';
import { Input } from '../components/ui/Input';
import { Modal } from '../components/ui/Modal';
import { useToast } from '../contexts/ToastContext';
import {
  Landmark,
  Plus,
  Trash2,
  Edit2,
  DollarSign,
  Briefcase,
  TrendingUp,
  Loader2
} from 'lucide-react';
import type { Account } from '../types';

export const Accounts: React.FC = () => {
  const queryClient = useQueryClient();
  const toast = useToast();

  const [isAddOpen, setIsAddOpen] = useState(false);
  const [isEditOpen, setIsEditOpen] = useState(false);
  const [selectedAcc, setSelectedAcc] = useState<Account | null>(null);

  // Form states
  const [formName, setFormName] = useState('');
  const [formType, setFormType] = useState('checking');
  const [formBalance, setFormBalance] = useState<number>(0);
  const [formCurrency, setFormCurrency] = useState('INR');

  // Query Accounts
  const { data: accounts = [], isLoading } = useQuery({
    queryKey: ['accounts'],
    queryFn: apiService.getAccounts,
  });

  // Create account mutation
  const createMutation = useMutation({
    mutationFn: apiService.createAccount,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['accounts'] });
      queryClient.invalidateQueries({ queryKey: ['dashboard'] });
      toast.showToast('Account added successfully', 'success');
      setIsAddOpen(false);
      resetForm();
    },
    onError: (err: any) => {
      toast.showToast(err.message || 'Failed to create account', 'error');
    },
  });

  // Update account mutation
  const updateMutation = useMutation({
    mutationFn: ({ id, data }: { id: number; data: any }) => apiService.updateAccount(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['accounts'] });
      queryClient.invalidateQueries({ queryKey: ['dashboard'] });
      toast.showToast('Account updated successfully', 'success');
      setIsEditOpen(false);
      setSelectedAcc(null);
      resetForm();
    },
    onError: (err: any) => {
      toast.showToast(err.message || 'Failed to update account', 'error');
    },
  });

  // Delete account mutation
  const deleteMutation = useMutation({
    mutationFn: apiService.deleteAccount,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['accounts'] });
      queryClient.invalidateQueries({ queryKey: ['dashboard'] });
      toast.showToast('Account deleted successfully', 'success');
    },
    onError: (err: any) => {
      toast.showToast(err.message || 'Failed to delete account', 'error');
    },
  });

  const resetForm = () => {
    setFormName('');
    setFormType('checking');
    setFormBalance(0);
    setFormCurrency('INR');
  };

  const handleCreateSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!formName.trim()) {
      toast.showToast('Please enter an account name', 'info');
      return;
    }

    createMutation.mutate({
      name: formName,
      account_type: formType,
      balance: formBalance,
      currency: formCurrency,
    });
  };

  const handleEditSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedAcc) return;
    if (!formName.trim()) {
      toast.showToast('Account name cannot be empty', 'info');
      return;
    }

    updateMutation.mutate({
      id: selectedAcc.id,
      data: {
        name: formName,
        account_type: formType,
        balance: formBalance,
        currency: formCurrency,
      },
    });
  };

  const handleEditOpen = (acc: Account) => {
    setSelectedAcc(acc);
    setFormName(acc.name);
    setFormType(acc.account_type);
    setFormBalance(acc.balance);
    setFormCurrency(acc.currency);
    setIsEditOpen(true);
  };

  const handleDelete = (id: number) => {
    if (window.confirm('Deleting this account will not delete associated transactions, but the account will no longer be visible. Proceed?')) {
      deleteMutation.mutate(id);
    }
  };

  const getAccountTypeIcon = (type: string) => {
    switch (type.toLowerCase()) {
      case 'checking':
      case 'savings':
      default:
        return <Landmark className="w-5 h-5 text-indigo-500" />;
      case 'investment':
        return <TrendingUp className="w-5 h-5 text-emerald-500" />;
      case 'credit':
      case 'loan':
        return <Briefcase className="w-5 h-5 text-amber-500" />;
    }
  };

  return (
    <div className="flex flex-col gap-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h2 className="text-xl md:text-2xl font-extrabold text-slate-850 dark:text-slate-100 tracking-tight">
            Accounts Registry
          </h2>
          <p className="text-sm text-slate-500 dark:text-slate-400 mt-1">
            Create, update, and manage your linked bank, savings, or investment accounts.
          </p>
        </div>
        <Button onClick={() => { resetForm(); setIsAddOpen(true); }} leftIcon={<Plus className="w-4 h-4" />}>
          Add Account
        </Button>
      </div>

      {/* Main Grid */}
      {isLoading ? (
        <div className="flex flex-col items-center justify-center min-h-[30vh] gap-3">
          <Loader2 className="w-8 h-8 animate-spin text-indigo-650" />
          <span className="text-xs text-slate-500 font-medium">Fetching accounts...</span>
        </div>
      ) : accounts.length === 0 ? (
        <Card className="py-12 text-center max-w-md mx-auto mt-6">
          <CardContent className="flex flex-col items-center justify-center p-8">
            <Landmark className="w-12 h-12 text-slate-350 mb-3" />
            <h4 className="text-base font-bold text-slate-805 dark:text-slate-205">No Accounts Found</h4>
            <p className="text-xs text-slate-500 mt-1 mb-6">Create a bank or credit account to start logging movements.</p>
            <Button onClick={() => { resetForm(); setIsAddOpen(true); }} leftIcon={<Plus className="w-4 h-4" />}>
              Link First Account
            </Button>
          </CardContent>
        </Card>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {accounts.map((acc) => {
            const formattedBalance = new Intl.NumberFormat('en-IN', {
              style: 'currency',
              currency: acc.currency,
              maximumFractionDigits: 0
            }).format(acc.balance);

            return (
              <Card key={acc.id} className="relative overflow-hidden group hover:shadow-xl transition-all duration-200">
                <CardContent className="p-6 flex flex-col justify-between h-full gap-5">
                  <div className="flex items-start justify-between gap-3">
                    <div className="flex items-center gap-3">
                      <div className="p-3 bg-slate-50 dark:bg-slate-900/60 border border-slate-100 dark:border-slate-800 rounded-xl">
                        {getAccountTypeIcon(acc.account_type)}
                      </div>
                      <div className="flex flex-col text-left">
                        <span className="text-sm font-black text-slate-800 dark:text-slate-100 group-hover:text-indigo-600 dark:group-hover:text-indigo-400 transition-colors">
                          {acc.name}
                        </span>
                        <span className="text-[10px] text-slate-455 font-bold uppercase tracking-wider mt-0.5">
                          {acc.account_type}
                        </span>
                      </div>
                    </div>

                    <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                      <button
                        onClick={() => handleEditOpen(acc)}
                        className="p-1.5 hover:bg-slate-100 dark:hover:bg-slate-800 rounded-lg text-slate-400 hover:text-indigo-650"
                        title="Edit Account"
                      >
                        <Edit2 className="w-3.5 h-3.5" />
                      </button>
                      <button
                        onClick={() => handleDelete(acc.id)}
                        className="p-1.5 hover:bg-slate-100 dark:hover:bg-slate-800 rounded-lg text-slate-400 hover:text-rose-600"
                        title="Delete Account"
                      >
                        <Trash2 className="w-3.5 h-3.5" />
                      </button>
                    </div>
                  </div>

                  <div className="text-left mt-3">
                    <span className="text-[10px] font-semibold text-slate-400 uppercase tracking-wider block">
                      Current Balance
                    </span>
                    <span className="text-3xl font-black text-slate-805 dark:text-slate-50 tracking-tight mt-1 block">
                      {formattedBalance}
                    </span>
                  </div>
                </CardContent>
              </Card>
            );
          })}
        </div>
      )}

      {/* MODAL: ADD ACCOUNT */}
      <Modal isOpen={isAddOpen} onClose={() => setIsAddOpen(false)} title="Add New Account">
        <form onSubmit={handleCreateSubmit} className="flex flex-col gap-4">
          <Input
            label="Account Name"
            type="text"
            placeholder="e.g. HDFC Salary Account"
            value={formName}
            onChange={(e) => setFormName(e.target.value)}
            required
          />

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div className="flex flex-col gap-1.5">
              <label className="text-xs font-semibold text-slate-655 dark:text-slate-400">Account Type</label>
              <select
                value={formType}
                onChange={(e) => setFormType(e.target.value)}
                className="w-full px-3.5 py-2.5 rounded-xl border border-slate-350 dark:border-slate-800 bg-white/50 dark:bg-slate-900/50 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500/50"
              >
                <option value="checking">Checking / Current</option>
                <option value="savings">Savings Account</option>
                <option value="investment">Investment Portfolio</option>
                <option value="credit">Credit Card</option>
                <option value="loan">Loan Liability</option>
              </select>
            </div>

            <div className="flex flex-col gap-1.5">
              <label className="text-xs font-semibold text-slate-655 dark:text-slate-400">Currency</label>
              <select
                value={formCurrency}
                onChange={(e) => setFormCurrency(e.target.value)}
                className="w-full px-3.5 py-2.5 rounded-xl border border-slate-350 dark:border-slate-800 bg-white/50 dark:bg-slate-900/50 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500/50"
              >
                <option value="INR">INR (₹)</option>
                <option value="USD">USD ($)</option>
                <option value="EUR">EUR (€)</option>
                <option value="GBP">GBP (£)</option>
              </select>
            </div>
          </div>

          <Input
            label="Initial Balance"
            type="number"
            step="0.01"
            value={formBalance || ''}
            onChange={(e) => setFormBalance(Number(e.target.value))}
            leftIcon={<DollarSign className="w-4 h-4" />}
            required
          />

          <div className="flex justify-end gap-2.5 mt-4">
            <Button type="button" variant="outline" onClick={() => setIsAddOpen(false)}>
              Cancel
            </Button>
            <Button type="submit" isLoading={createMutation.isPending}>
              Add Account
            </Button>
          </div>
        </form>
      </Modal>

      {/* MODAL: EDIT ACCOUNT */}
      <Modal isOpen={isEditOpen} onClose={() => setIsEditOpen(false)} title="Edit Account Details">
        <form onSubmit={handleEditSubmit} className="flex flex-col gap-4">
          <Input
            label="Account Name"
            type="text"
            placeholder="e.g. HDFC Salary Account"
            value={formName}
            onChange={(e) => setFormName(e.target.value)}
            required
          />

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div className="flex flex-col gap-1.5">
              <label className="text-xs font-semibold text-slate-655 dark:text-slate-400">Account Type</label>
              <select
                value={formType}
                onChange={(e) => setFormType(e.target.value)}
                className="w-full px-3.5 py-2.5 rounded-xl border border-slate-350 dark:border-slate-800 bg-white/50 dark:bg-slate-900/50 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500/50"
              >
                <option value="checking">Checking / Current</option>
                <option value="savings">Savings Account</option>
                <option value="investment">Investment Portfolio</option>
                <option value="credit">Credit Card</option>
                <option value="loan">Loan Liability</option>
              </select>
            </div>

            <div className="flex flex-col gap-1.5">
              <label className="text-xs font-semibold text-slate-655 dark:text-slate-400">Currency</label>
              <select
                value={formCurrency}
                onChange={(e) => setFormCurrency(e.target.value)}
                className="w-full px-3.5 py-2.5 rounded-xl border border-slate-350 dark:border-slate-800 bg-white/50 dark:bg-slate-900/50 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500/50"
              >
                <option value="INR">INR (₹)</option>
                <option value="USD">USD ($)</option>
                <option value="EUR">EUR (€)</option>
                <option value="GBP">GBP (£)</option>
              </select>
            </div>
          </div>

          <Input
            label="Account Balance"
            type="number"
            step="0.01"
            value={formBalance || ''}
            onChange={(e) => setFormBalance(Number(e.target.value))}
            leftIcon={<DollarSign className="w-4 h-4" />}
            required
          />

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
export default Accounts;
