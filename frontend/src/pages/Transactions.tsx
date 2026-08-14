import React, { useState, useEffect } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { apiService } from '../services/apiService';
import { Card, CardContent } from '../components/ui/Card';
import { Button } from '../components/ui/Button';
import { Input } from '../components/ui/Input';
import { Badge } from '../components/ui/Badge';
import { Table, TableRow, TableCell } from '../components/ui/Table';
import { Modal } from '../components/ui/Modal';
import { useToast } from '../contexts/ToastContext';
import { useLocation } from 'react-router-dom';
import {
  Search,
  Plus,
  Trash2,
  Edit2,
  Download,
  Filter,
  ChevronLeft,
  ChevronRight,
  Loader2,
  Calendar,
  Tag,
  DollarSign
} from 'lucide-react';
import type { Transaction } from '../types';

export const Transactions: React.FC = () => {
  const queryClient = useQueryClient();
  const toast = useToast();
  const location = useLocation();

  // State parameters
  const [searchQuery, setSearchQuery] = useState('');
  const [debouncedSearch, setDebouncedSearch] = useState('');
  const [limit] = useState(15);
  const [offset, setOffset] = useState(0);

  // Filters state
  const [filterAccount, setFilterAccount] = useState<number | undefined>(undefined);
  const [filterCategory, setFilterCategory] = useState<number | undefined>(undefined);
  const [filterType, setFilterType] = useState<string | undefined>(undefined);
  const [filterStartDate, setFilterStartDate] = useState('');
  const [filterEndDate, setFilterEndDate] = useState('');
  const [filterMerchant, setFilterMerchant] = useState('');

  // Modals state
  const [isAddOpen, setIsAddOpen] = useState(false);
  const [isEditOpen, setIsEditOpen] = useState(false);
  const [selectedTx, setSelectedTx] = useState<Transaction | null>(null);

  // Form states
  const [formAccount, setFormAccount] = useState<number>(0);
  const [formCategory, setFormCategory] = useState<number | undefined>(undefined);
  const [formType, setFormType] = useState<string>('expense');
  const [formTitle, setFormTitle] = useState('');
  const [formDescription, setFormDescription] = useState('');
  const [formAmount, setFormAmount] = useState<number>(0);
  const [formDate, setFormDate] = useState<string>(new Date().toISOString().split('T')[0]);
  const [formMerchant, setFormMerchant] = useState('');
  const [formPaymentMethod, setFormPaymentMethod] = useState('');
  const [formLocation, setFormLocation] = useState('');
  const [formTagsString, setFormTagsString] = useState('');

  // Check URL query parameters (for quick add from dashboard)
  useEffect(() => {
    const params = new URLSearchParams(location.search);
    if (params.get('add') === 'true') {
      setIsAddOpen(true);
    }
  }, [location]);

  // Debounce search query
  useEffect(() => {
    const timer = setTimeout(() => {
      setDebouncedSearch(searchQuery);
      setOffset(0); // reset page on search
    }, 450);
    return () => clearTimeout(timer);
  }, [searchQuery]);

  // Query helper data (Accounts, Categories)
  const { data: accounts = [] } = useQuery({
    queryKey: ['accounts'],
    queryFn: apiService.getAccounts,
  });

  const { data: categories = [] } = useQuery({
    queryKey: ['categories'],
    queryFn: apiService.getCategories,
  });

  // Main Transactions Query (Search vs Filters)
  const isSearchActive = !!debouncedSearch;
  const transactionParams = {
    limit,
    offset,
    account_id: filterAccount || undefined,
    category_id: filterCategory || undefined,
    transaction_type: filterType || undefined,
    start_date: filterStartDate || undefined,
    end_date: filterEndDate || undefined,
    merchant: filterMerchant || undefined,
  };

  const { data: txPage, isLoading } = useQuery({
    queryKey: ['transactions', isSearchActive, debouncedSearch, transactionParams],
    queryFn: () => {
      if (isSearchActive) {
        return apiService.searchTransactions({
          query: debouncedSearch,
          limit,
          offset,
        });
      } else {
        return apiService.getTransactions(transactionParams);
      }
    },
  });

  // Mutators: Create, Update, Delete
  const createMutation = useMutation({
    mutationFn: apiService.createTransaction,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['transactions'] });
      queryClient.invalidateQueries({ queryKey: ['dashboard'] });
      toast.showToast('Transaction recorded successfully', 'success');
      setIsAddOpen(false);
      resetForm();
    },
    onError: (err: any) => {
      toast.showToast(err.message || 'Failed to create transaction', 'error');
    },
  });

  const updateMutation = useMutation({
    mutationFn: ({ id, data }: { id: number; data: any }) => apiService.updateTransaction(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['transactions'] });
      queryClient.invalidateQueries({ queryKey: ['dashboard'] });
      toast.showToast('Transaction updated successfully', 'success');
      setIsEditOpen(false);
      setSelectedTx(null);
      resetForm();
    },
    onError: (err: any) => {
      toast.showToast(err.message || 'Failed to update transaction', 'error');
    },
  });

  const deleteMutation = useMutation({
    mutationFn: apiService.deleteTransaction,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['transactions'] });
      queryClient.invalidateQueries({ queryKey: ['dashboard'] });
      toast.showToast('Transaction deleted successfully', 'success');
    },
    onError: (err: any) => {
      toast.showToast(err.message || 'Failed to delete transaction', 'error');
    },
  });

  const resetForm = () => {
    setFormAccount(0);
    setFormCategory(undefined);
    setFormType('expense');
    setFormTitle('');
    setFormDescription('');
    setFormAmount(0);
    setFormDate(new Date().toISOString().split('T')[0]);
    setFormMerchant('');
    setFormPaymentMethod('');
    setFormLocation('');
    setFormTagsString('');
  };

  const handleCreateSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (formAmount <= 0) {
      toast.showToast('Amount must be greater than zero', 'info');
      return;
    }
    if (formAccount === 0) {
      toast.showToast('Please select a valid account', 'info');
      return;
    }

    const tags = formTagsString
      ? formTagsString.split(',').map((t) => t.trim().toLowerCase()).filter(Boolean)
      : [];

    createMutation.mutate({
      account_id: formAccount,
      category_id: formCategory || undefined,
      transaction_type: formType,
      title: formTitle,
      description: formDescription || undefined,
      amount: formAmount,
      transaction_date: formDate,
      merchant: formMerchant || undefined,
      payment_method: formPaymentMethod || undefined,
      location: formLocation || undefined,
      tags,
    });
  };

  const handleEditSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedTx) return;
    if (formAmount <= 0) {
      toast.showToast('Amount must be greater than zero', 'info');
      return;
    }

    const tags = formTagsString
      ? formTagsString.split(',').map((t) => t.trim().toLowerCase()).filter(Boolean)
      : [];

    updateMutation.mutate({
      id: selectedTx.id,
      data: {
        account_id: formAccount,
        category_id: formCategory || null,
        transaction_type: formType,
        title: formTitle,
        description: formDescription || null,
        amount: formAmount,
        transaction_date: formDate,
        merchant: formMerchant || null,
        payment_method: formPaymentMethod || null,
        location: formLocation || null,
        tags,
      },
    });
  };

  const handleEditOpen = (tx: Transaction) => {
    setSelectedTx(tx);
    setFormAccount(tx.account_id);
    setFormCategory(tx.category_id || undefined);
    setFormType(tx.transaction_type);
    setFormTitle(tx.title);
    setFormDescription(tx.description || '');
    setFormAmount(Number(tx.amount));
    setFormDate(tx.transaction_date);
    setFormMerchant(tx.merchant || '');
    setFormPaymentMethod(tx.payment_method || '');
    setFormLocation(tx.location || '');
    setFormTagsString(tx.tags.join(', '));
    setIsEditOpen(true);
  };

  const handleDelete = (id: number) => {
    if (window.confirm('Are you sure you want to delete this transaction?')) {
      deleteMutation.mutate(id);
    }
  };

  // Local client-side CSV export
  const handleExportCSV = () => {
    if (!txPage || txPage.items.length === 0) {
      toast.showToast('No transactions to export', 'info');
      return;
    }

    const headers = ['ID', 'Date', 'Title', 'Type', 'Amount', 'Account', 'Category', 'Merchant', 'Tags'];
    const rows = txPage.items.map((tx) => {
      const accName = accounts.find((a) => a.id === tx.account_id)?.name || tx.account_id;
      const catName = categories.find((c) => c.id === tx.category_id)?.name || 'Uncategorized';
      return [
        tx.id,
        tx.transaction_date,
        `"${tx.title.replace(/"/g, '""')}"`,
        tx.transaction_type,
        tx.amount,
        `"${accName}"`,
        `"${catName}"`,
        `"${(tx.merchant || '').replace(/"/g, '""')}"`,
        `"${tx.tags.join(',')}"`,
      ];
    });

    const csvContent =
      'data:text/csv;charset=utf-8,' +
      [headers.join(','), ...rows.map((e) => e.join(','))].join('\n');
    
    const encodedUri = encodeURI(csvContent);
    const link = document.createElement('a');
    link.setAttribute('href', encodedUri);
    link.setAttribute('download', `transactions_export_${new Date().toISOString().split('T')[0]}.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  const items = txPage?.items || [];
  const totalItems = txPage?.total || 0;
  const totalPages = Math.ceil(totalItems / limit);
  const currentPage = Math.floor(offset / limit) + 1;

  return (
    <div className="flex flex-col gap-6">
      {/* Header Panel */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h2 className="text-xl md:text-2xl font-extrabold text-slate-850 dark:text-slate-100 tracking-tight">
            Transactions Log
          </h2>
          <p className="text-sm text-slate-500 dark:text-slate-400 mt-1">
            Browse and filter your registered financial movements.
          </p>
        </div>
        <div className="flex gap-2">
          <Button onClick={handleExportCSV} variant="outline" leftIcon={<Download className="w-4 h-4" />}>
            Export CSV
          </Button>
          <Button onClick={() => { resetForm(); setIsAddOpen(true); }} leftIcon={<Plus className="w-4 h-4" />}>
            New Transaction
          </Button>
        </div>
      </div>

      {/* Filter and Search Panel */}
      <Card>
        <CardContent className="p-4 flex flex-col gap-4">
          <div className="flex flex-col md:flex-row gap-3">
            {/* Search Input */}
            <div className="relative flex-1">
              <Search className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400 pointer-events-none" />
              <input
                type="text"
                placeholder="Search transactions by title or description..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-full pl-10 pr-4 py-2.5 rounded-xl border border-slate-300 dark:border-slate-800 bg-white/50 dark:bg-slate-900/50 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500/50"
              />
            </div>

            {/* Type Filter */}
            <select
              value={filterType || ''}
              onChange={(e) => { setFilterType(e.target.value || undefined); setOffset(0); }}
              className="px-3.5 py-2.5 rounded-xl border border-slate-300 dark:border-slate-800 bg-white/50 dark:bg-slate-900/50 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500/50"
            >
              <option value="">All Types</option>
              <option value="income">Income</option>
              <option value="expense">Expense</option>
              <option value="transfer">Transfer</option>
            </select>

            {/* Account Filter */}
            <select
              value={filterAccount || ''}
              onChange={(e) => { setFilterAccount(Number(e.target.value) || undefined); setOffset(0); }}
              className="px-3.5 py-2.5 rounded-xl border border-slate-300 dark:border-slate-800 bg-white/50 dark:bg-slate-900/50 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500/50"
            >
              <option value="">All Accounts</option>
              {accounts.map((acc) => (
                <option key={acc.id} value={acc.id}>{acc.name}</option>
              ))}
            </select>

            {/* Category Filter */}
            <select
              value={filterCategory || ''}
              onChange={(e) => { setFilterCategory(Number(e.target.value) || undefined); setOffset(0); }}
              className="px-3.5 py-2.5 rounded-xl border border-slate-300 dark:border-slate-800 bg-white/50 dark:bg-slate-900/50 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500/50"
            >
              <option value="">All Categories</option>
              {categories.map((cat) => (
                <option key={cat.id} value={cat.id}>{cat.name}</option>
              ))}
            </select>
          </div>

          {/* Advanced filter toggles */}
          <details className="text-xs text-slate-500">
            <summary className="cursor-pointer font-bold hover:underline outline-none select-none flex items-center gap-1.5 w-fit">
              <Filter className="w-3.5 h-3.5 text-indigo-500" /> More Filters (Date range, Merchant)
            </summary>
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 mt-3 pt-3 border-t border-slate-100 dark:border-slate-800">
              <Input
                label="Start Date"
                type="date"
                value={filterStartDate}
                onChange={(e) => { setFilterStartDate(e.target.value); setOffset(0); }}
              />
              <Input
                label="End Date"
                type="date"
                value={filterEndDate}
                onChange={(e) => { setFilterEndDate(e.target.value); setOffset(0); }}
              />
              <Input
                label="Merchant Name"
                placeholder="e.g. Amazon"
                value={filterMerchant}
                onChange={(e) => { setFilterMerchant(e.target.value); setOffset(0); }}
              />
            </div>
          </details>
        </CardContent>
      </Card>

      {/* Main Table Panel */}
      {isLoading ? (
        <div className="flex flex-col items-center justify-center min-h-[30vh] gap-3">
          <Loader2 className="w-8 h-8 animate-spin text-indigo-650" />
          <span className="text-xs text-slate-500 font-medium">Fetching transactions...</span>
        </div>
      ) : items.length === 0 ? (
        <Card className="py-12 text-center">
          <CardContent className="flex flex-col items-center justify-center p-8">
            <Filter className="w-12 h-12 text-slate-350 mb-3" />
            <h4 className="text-base font-bold text-slate-800 dark:text-slate-205">No transactions found</h4>
            <p className="text-xs text-slate-500 mt-1">Try relaxing your filter parameters or search terms.</p>
          </CardContent>
        </Card>
      ) : (
        <div className="flex flex-col gap-4">
          <Table headers={['Date', 'Title', 'Category', 'Account', 'Merchant', 'Type', 'Amount', 'Actions']}>
            {items.map((tx) => {
              const accName = accounts.find((a) => a.id === tx.account_id)?.name || `Account #${tx.account_id}`;
              const cat = categories.find((c) => c.id === tx.category_id);
              const catName = cat?.name || 'Uncategorized';
              const catColor = cat?.color || '#94a3b8';

              const isExpense = tx.transaction_type === 'expense';
              const isIncome = tx.transaction_type === 'income';

              return (
                <TableRow key={tx.id}>
                  <TableCell className="whitespace-nowrap font-medium text-slate-500">
                    {new Date(tx.transaction_date).toLocaleDateString()}
                  </TableCell>
                  <TableCell className="max-w-[200px]">
                    <div className="flex flex-col text-left">
                      <span className="font-bold text-slate-805 dark:text-slate-200 truncate">{tx.title}</span>
                      {tx.description && <span className="text-[10px] text-slate-450 dark:text-slate-400 truncate">{tx.description}</span>}
                    </div>
                  </TableCell>
                  <TableCell>
                    <div className="flex items-center gap-1.5">
                      <span className="w-2.5 h-2.5 rounded-full shrink-0" style={{ backgroundColor: catColor }} />
                      <span className="font-semibold text-slate-600 dark:text-slate-350">{catName}</span>
                    </div>
                  </TableCell>
                  <TableCell className="font-semibold text-slate-600 dark:text-slate-350">{accName}</TableCell>
                  <TableCell className="font-medium text-slate-500">{tx.merchant || '-'}</TableCell>
                  <TableCell>
                    <Badge variant={isIncome ? 'success' : isExpense ? 'danger' : 'info'} className="uppercase text-[9px] px-2">
                      {tx.transaction_type}
                    </Badge>
                  </TableCell>
                  <TableCell className={`font-black whitespace-nowrap text-right ${isIncome ? 'text-emerald-600' : isExpense ? 'text-rose-600' : 'text-slate-700 dark:text-slate-300'}`}>
                    {isIncome ? '+' : isExpense ? '-' : ''}₹{tx.amount}
                  </TableCell>
                  <TableCell>
                    <div className="flex items-center gap-2">
                      <button
                        onClick={() => handleEditOpen(tx)}
                        className="p-1.5 hover:bg-slate-100 dark:hover:bg-slate-800 rounded-lg text-slate-400 hover:text-indigo-650 dark:hover:text-indigo-400 transition-colors"
                        title="Edit"
                      >
                        <Edit2 className="w-4 h-4" />
                      </button>
                      <button
                        onClick={() => handleDelete(tx.id)}
                        className="p-1.5 hover:bg-slate-100 dark:hover:bg-slate-800 rounded-lg text-slate-400 hover:text-rose-600 dark:hover:text-rose-450 transition-colors"
                        title="Delete"
                      >
                        <Trash2 className="w-4 h-4" />
                      </button>
                    </div>
                  </TableCell>
                </TableRow>
              );
            })}
          </Table>

          {/* Pagination Controls */}
          {totalPages > 1 && (
            <div className="flex items-center justify-between mt-3 bg-white/20 dark:bg-slate-900/5 backdrop-blur-sm p-4 rounded-xl border border-slate-200/50 dark:border-slate-800/50">
              <span className="text-xs text-slate-500 font-semibold">
                Page {currentPage} of {totalPages} ({totalItems} items)
              </span>
              <div className="flex gap-2">
                <Button
                  onClick={() => setOffset((o) => Math.max(0, o - limit))}
                  disabled={currentPage === 1}
                  variant="outline"
                  size="sm"
                  leftIcon={<ChevronLeft className="w-4 h-4" />}
                >
                  Previous
                </Button>
                <Button
                  onClick={() => setOffset((o) => o + limit)}
                  disabled={currentPage === totalPages}
                  variant="outline"
                  size="sm"
                  rightIcon={<ChevronRight className="w-4 h-4" />}
                >
                  Next
                </Button>
              </div>
            </div>
          )}
        </div>
      )}

      {/* MODAL: ADD TRANSACTION */}
      <Modal isOpen={isAddOpen} onClose={() => setIsAddOpen(false)} title="Create New Transaction">
        <form onSubmit={handleCreateSubmit} className="flex flex-col gap-4">
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div className="flex flex-col gap-1.5">
              <label className="text-xs font-semibold text-slate-655 dark:text-slate-400">Account</label>
              {accounts.length === 0 ? (
                <div className="p-2.5 bg-rose-50 dark:bg-rose-950/20 text-rose-605 dark:text-rose-400 border border-rose-250/30 rounded-xl text-xs font-semibold">
                  You don't have any accounts. Please create one first!
                </div>
              ) : (
                <select
                  value={formAccount || ''}
                  onChange={(e) => setFormAccount(Number(e.target.value) || 0)}
                  className="w-full px-3.5 py-2.5 rounded-xl border border-slate-350 dark:border-slate-800 bg-white/50 dark:bg-slate-900/50 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500/50"
                  required
                >
                  <option value="">-- Select Account --</option>
                  {accounts.map((a) => (
                    <option key={a.id} value={a.id}>{a.name} (₹{a.balance})</option>
                  ))}
                </select>
              )}
            </div>

            <div className="flex flex-col gap-1.5">
              <label className="text-xs font-semibold text-slate-655 dark:text-slate-400">Category</label>
              <select
                value={formCategory || ''}
                onChange={(e) => setFormCategory(Number(e.target.value) || undefined)}
                className="w-full px-3.5 py-2.5 rounded-xl border border-slate-350 dark:border-slate-800 bg-white/50 dark:bg-slate-900/50 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500/50"
              >
                <option value="">Uncategorized</option>
                {categories.map((c) => (
                  <option key={c.id} value={c.id}>{c.name}</option>
                ))}
              </select>
            </div>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div className="flex flex-col gap-1.5">
              <label className="text-xs font-semibold text-slate-655 dark:text-slate-400">Type</label>
              <select
                value={formType}
                onChange={(e) => setFormType(e.target.value)}
                className="w-full px-3.5 py-2.5 rounded-xl border border-slate-350 dark:border-slate-800 bg-white/50 dark:bg-slate-900/50 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500/50"
              >
                <option value="expense">Expense</option>
                <option value="income">Income</option>
                <option value="transfer">Transfer</option>
              </select>
            </div>

            <Input
              label="Amount (INR)"
              type="number"
              step="0.01"
              value={formAmount || ''}
              onChange={(e) => setFormAmount(Number(e.target.value))}
              leftIcon={<DollarSign className="w-4 h-4" />}
              required
            />
          </div>

          <Input
            label="Transaction Title"
            type="text"
            placeholder="e.g. Weekly Grocery Run"
            value={formTitle}
            onChange={(e) => setFormTitle(e.target.value)}
            required
          />

          <Input
            label="Description"
            type="text"
            placeholder="e.g. Bought items at supermarket"
            value={formDescription}
            onChange={(e) => setFormDescription(e.target.value)}
          />

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <Input
              label="Transaction Date"
              type="date"
              value={formDate}
              onChange={(e) => setFormDate(e.target.value)}
              leftIcon={<Calendar className="w-4 h-4" />}
              required
            />

            <Input
              label="Merchant"
              type="text"
              placeholder="e.g. DMart"
              value={formMerchant}
              onChange={(e) => setFormMerchant(e.target.value)}
            />
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <Input
              label="Payment Method"
              type="text"
              placeholder="e.g. UPI / Credit Card"
              value={formPaymentMethod}
              onChange={(e) => setFormPaymentMethod(e.target.value)}
            />

            <Input
              label="Location"
              type="text"
              placeholder="e.g. Mumbai, MH"
              value={formLocation}
              onChange={(e) => setFormLocation(e.target.value)}
            />
          </div>

          <Input
            label="Tags (comma separated)"
            type="text"
            placeholder="grocery, food, weekly"
            value={formTagsString}
            onChange={(e) => setFormTagsString(e.target.value)}
            leftIcon={<Tag className="w-4 h-4" />}
          />

          <div className="flex justify-end gap-2.5 mt-4">
            <Button type="button" variant="outline" onClick={() => setIsAddOpen(false)}>
              Cancel
            </Button>
            <Button type="submit" isLoading={createMutation.isPending}>
              Create Record
            </Button>
          </div>
        </form>
      </Modal>

      {/* MODAL: EDIT TRANSACTION */}
      <Modal isOpen={isEditOpen} onClose={() => setIsEditOpen(false)} title="Edit Transaction Details">
        <form onSubmit={handleEditSubmit} className="flex flex-col gap-4">
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div className="flex flex-col gap-1.5">
              <label className="text-xs font-semibold text-slate-655 dark:text-slate-400">Account</label>
              {accounts.length === 0 ? (
                <div className="p-2.5 bg-rose-50 dark:bg-rose-950/20 text-rose-605 dark:text-rose-400 border border-rose-250/30 rounded-xl text-xs font-semibold">
                  You don't have any accounts. Please create one first!
                </div>
              ) : (
                <select
                  value={formAccount || ''}
                  onChange={(e) => setFormAccount(Number(e.target.value) || 0)}
                  className="w-full px-3.5 py-2.5 rounded-xl border border-slate-350 dark:border-slate-800 bg-white/50 dark:bg-slate-900/50 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500/50"
                  required
                >
                  <option value="">-- Select Account --</option>
                  {accounts.map((a) => (
                    <option key={a.id} value={a.id}>{a.name} (₹{a.balance})</option>
                  ))}
                </select>
              )}
            </div>

            <div className="flex flex-col gap-1.5">
              <label className="text-xs font-semibold text-slate-655 dark:text-slate-400">Category</label>
              <select
                value={formCategory || ''}
                onChange={(e) => setFormCategory(Number(e.target.value) || undefined)}
                className="w-full px-3.5 py-2.5 rounded-xl border border-slate-350 dark:border-slate-800 bg-white/50 dark:bg-slate-900/50 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500/50"
              >
                <option value="">Uncategorized</option>
                {categories.map((c) => (
                  <option key={c.id} value={c.id}>{c.name}</option>
                ))}
              </select>
            </div>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div className="flex flex-col gap-1.5">
              <label className="text-xs font-semibold text-slate-655 dark:text-slate-400">Type</label>
              <select
                value={formType}
                onChange={(e) => setFormType(e.target.value)}
                className="w-full px-3.5 py-2.5 rounded-xl border border-slate-350 dark:border-slate-800 bg-white/50 dark:bg-slate-900/50 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500/50"
              >
                <option value="expense">Expense</option>
                <option value="income">Income</option>
                <option value="transfer">Transfer</option>
              </select>
            </div>

            <Input
              label="Amount (INR)"
              type="number"
              step="0.01"
              value={formAmount || ''}
              onChange={(e) => setFormAmount(Number(e.target.value))}
              leftIcon={<DollarSign className="w-4 h-4" />}
              required
            />
          </div>

          <Input
            label="Transaction Title"
            type="text"
            placeholder="e.g. Weekly Grocery Run"
            value={formTitle}
            onChange={(e) => setFormTitle(e.target.value)}
            required
          />

          <Input
            label="Description"
            type="text"
            placeholder="e.g. Bought items at supermarket"
            value={formDescription}
            onChange={(e) => setFormDescription(e.target.value)}
          />

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <Input
              label="Transaction Date"
              type="date"
              value={formDate}
              onChange={(e) => setFormDate(e.target.value)}
              leftIcon={<Calendar className="w-4 h-4" />}
              required
            />

            <Input
              label="Merchant"
              type="text"
              placeholder="e.g. DMart"
              value={formMerchant}
              onChange={(e) => setFormMerchant(e.target.value)}
            />
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <Input
              label="Payment Method"
              type="text"
              placeholder="e.g. UPI / Credit Card"
              value={formPaymentMethod}
              onChange={(e) => setFormPaymentMethod(e.target.value)}
            />

            <Input
              label="Location"
              type="text"
              placeholder="e.g. Mumbai, MH"
              value={formLocation}
              onChange={(e) => setFormLocation(e.target.value)}
            />
          </div>

          <Input
            label="Tags (comma separated)"
            type="text"
            placeholder="grocery, food, weekly"
            value={formTagsString}
            onChange={(e) => setFormTagsString(e.target.value)}
            leftIcon={<Tag className="w-4 h-4" />}
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
export default Transactions;
