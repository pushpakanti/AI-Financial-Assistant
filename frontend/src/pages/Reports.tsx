import React, { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { apiService } from '../services/apiService';
import { Card, CardHeader, CardTitle, CardContent } from '../components/ui/Card';
import { Button } from '../components/ui/Button';
import { Input } from '../components/ui/Input';
import { Table, TableRow, TableCell } from '../components/ui/Table';
import { Badge } from '../components/ui/Badge';
import { useToast } from '../contexts/ToastContext';
import {
  AlertTriangle,
  BarChart3,
  Calendar,
  Download,
  FileText,
  Loader2,
  PieChart as PieIcon,
  TrendingDown,
  TrendingUp,
  Wallet
} from 'lucide-react';
import { ResponsiveContainer, PieChart, Pie, Cell, Tooltip } from 'recharts';

export const Reports: React.FC = () => {
  const toast = useToast();

  const [startDate, setStartDate] = useState(() => {
    const d = new Date();
    d.setDate(1); // start of current month
    const year = d.getFullYear();
    const month = String(d.getMonth() + 1).padStart(2, '0');
    const day = String(d.getDate()).padStart(2, '0');
    return `${year}-${month}-${day}`;
  });

  const [endDate, setEndDate] = useState(() => {
    const d = new Date();
    const year = d.getFullYear();
    const month = String(d.getMonth() + 1).padStart(2, '0');
    const day = String(d.getDate()).padStart(2, '0');
    return `${year}-${month}-${day}`;
  });

  // Query Accounts
  const { data: accounts = [], isLoading: loadingAccounts } = useQuery({
    queryKey: ['accounts'],
    queryFn: apiService.getAccounts,
  });

  // Query Categories
  const { data: categories = [] } = useQuery({
    queryKey: ['categories'],
    queryFn: apiService.getCategories,
  });

  const isValidDateRange = !!startDate && !!endDate && startDate <= endDate;

  // Query Transactions within the selected range
  const { data: txPage, isLoading: loadingTx, isError } = useQuery({
    queryKey: ['reportTransactions', startDate, endDate],
    queryFn: async () => {
      try {
        let allItems: any[] = [];
        let offset = 0;
        const limit = 100;
        let hasMore = true;

        while (hasMore) {
          const response = await apiService.getTransactions({
            start_date: startDate,
            end_date: endDate,
            limit,
            offset,
          });

          const items = response.items || [];
          allItems = [...allItems, ...items];

          if (items.length < limit || allItems.length >= (response.total || 0)) {
            hasMore = false;
          } else {
            offset += limit;
          }
        }

        // Combine the pages without duplicating transactions
        const seenIds = new Set();
        const uniqueItems = allItems.filter(item => {
          if (seenIds.has(item.id)) {
            return false;
          }
          seenIds.add(item.id);
          return true;
        });

        return {
          items: uniqueItems,
          total: uniqueItems.length,
          limit: limit,
          offset: 0
        };
      } catch (err: any) {
        toast.showToast(err.message || 'Failed to fetch transaction reports data', 'error');
        throw err;
      }
    },
    enabled: isValidDateRange,
  });

  const transactions = txPage?.items || [];

  // Metrics computation
  let totalIncome = 0;
  let totalExpense = 0;
  const categorySums: Record<number, { name: string; amount: number; color: string }> = {};

  transactions.forEach((tx) => {
    const isIncome = tx.transaction_type.toLowerCase() === 'income';
    const isExpense = tx.transaction_type.toLowerCase() === 'expense';
    const amount = Number(tx.amount) || 0;

    if (isIncome) {
      totalIncome += amount;
    } else if (isExpense) {
      totalExpense += amount;
      
      const catId = tx.category_id || 0;
      const cat = categories.find((c) => c.id === catId);
      const catName = cat?.name || 'Uncategorized';
      const catColor = cat?.color || '#94a3b8';

      if (!categorySums[catId]) {
        categorySums[catId] = { name: catName, amount: 0, color: catColor };
      }
      categorySums[catId].amount += amount;
    }
  });

  const netSavings = totalIncome - totalExpense;
  const savingsRate = totalIncome > 0 ? Math.round((netSavings / totalIncome) * 100) : 0;

  // Chart Data preparation
  const chartData = Object.values(categorySums).map((cat) => ({
    name: cat.name,
    value: Math.round(cat.amount),
    color: cat.color,
  })).sort((a, b) => b.value - a.value);

  const COLORS = ['#4f46e5', '#8b5cf6', '#ec4899', '#f43f5e', '#f59e0b', '#10b981', '#06b6d4', '#3b82f6'];

  const handlePrint = () => {
    window.print();
  };

  const handleExportCSV = () => {
    if (transactions.length === 0) {
      toast.showToast('No transaction data to export', 'info');
      return;
    }

    const headers = ['Date', 'Title', 'Type', 'Amount', 'Account', 'Category', 'Merchant'];
    const rows = transactions.map((tx) => {
      const accName = accounts.find((a) => a.id === tx.account_id)?.name || tx.account_id;
      const catName = categories.find((c) => c.id === tx.category_id)?.name || 'Uncategorized';
      return [
        tx.transaction_date,
        `"${tx.title.replace(/"/g, '""')}"`,
        tx.transaction_type,
        tx.amount,
        `"${accName}"`,
        `"${catName}"`,
        `"${(tx.merchant || '').replace(/"/g, '""')}"`,
      ];
    });

    const csvContent =
      'data:text/csv;charset=utf-8,' +
      [headers.join(','), ...rows.map((e) => e.join(','))].join('\n');

    const encodedUri = encodeURI(csvContent);
    const link = document.createElement('a');
    link.setAttribute('href', encodedUri);
    link.setAttribute('download', `financial_report_${startDate}_to_${endDate}.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  const isDataAvailable = transactions.length > 0;
  const isLoading = loadingAccounts || loadingTx;

  return (
    <div className="flex flex-col gap-6 printable-area">
      {/* Header Panel */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-200/40 dark:border-slate-800/40 pb-4">
        <div>
          <h2 className="text-xl md:text-2xl font-extrabold text-slate-850 dark:text-slate-100 tracking-tight flex items-center gap-2">
            <FileText className="w-6 h-6 text-indigo-650" />
            Financial Reporting
          </h2>
          <p className="text-sm text-slate-500 dark:text-slate-400 mt-1">
            Build custom period reviews and export balance statements.
          </p>
        </div>
        <div className="flex gap-2 no-print">
          <Button onClick={handleExportCSV} variant="outline" leftIcon={<Download className="w-4 h-4" />}>
            Export CSV
          </Button>
          <Button onClick={handlePrint} leftIcon={<BarChart3 className="w-4 h-4" />}>
            Print Statement / PDF
          </Button>
        </div>
      </div>

      {/* Date Selectors (Hidden during printing) */}
      <Card className="no-print">
        <CardContent className="p-5 flex flex-col sm:flex-row items-center gap-4">
          <div className="w-full sm:w-fit flex items-center gap-2 text-xs font-semibold text-slate-500 uppercase tracking-wider shrink-0">
            <Calendar className="w-4.5 h-4.5 text-indigo-500" />
            Select Period:
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 w-full">
            <Input
              label="Start Date"
              type="date"
              value={startDate}
              onChange={(e) => setStartDate(e.target.value)}
            />
            <Input
              label="End Date"
              type="date"
              value={endDate}
              onChange={(e) => setEndDate(e.target.value)}
            />
          </div>
        </CardContent>
      </Card>

      {isLoading ? (
        <div className="flex flex-col items-center justify-center min-h-[30vh] gap-3">
          <Loader2 className="w-8 h-8 animate-spin text-indigo-650" />
          <span className="text-xs text-slate-550 dark:text-slate-400 font-medium">Compiling reporting details...</span>
        </div>
      ) : !isValidDateRange ? (
        <Card className="py-12 text-center max-w-md mx-auto mt-6 border-amber-200 dark:border-amber-900 bg-amber-50/50 dark:bg-amber-950/20">
          <CardContent className="flex flex-col items-center justify-center p-8">
            <AlertTriangle className="w-12 h-12 text-amber-500 mb-3" />
            <h4 className="text-base font-bold text-amber-805 dark:text-amber-205">Invalid Date Range</h4>
            <p className="text-xs text-slate-550 dark:text-slate-400 mt-1">Start date must be on or before end date.</p>
          </CardContent>
        </Card>
      ) : isError ? (
        <Card className="py-12 text-center max-w-md mx-auto mt-6 border-rose-200 dark:border-rose-900 bg-rose-50/50 dark:bg-rose-950/20">
          <CardContent className="flex flex-col items-center justify-center p-8">
            <FileText className="w-12 h-12 text-rose-500 mb-3" />
            <h4 className="text-base font-bold text-rose-805 dark:text-rose-205">Error Loading Report</h4>
            <p className="text-xs text-slate-500 mt-1">An error occurred while compiling transaction data. Please try again.</p>
          </CardContent>
        </Card>
      ) : !isDataAvailable ? (
        <Card className="py-12 text-center max-w-md mx-auto mt-6">
          <CardContent className="flex flex-col items-center justify-center p-8">
            <FileText className="w-12 h-12 text-slate-350 mb-3" />
            <h4 className="text-base font-bold text-slate-805 dark:text-slate-205">No Data in Selected Period</h4>
            <p className="text-xs text-slate-500 mt-1">Try expanding your date range parameters.</p>
          </CardContent>
        </Card>
      ) : (
        <div className="flex flex-col gap-6">
          {/* Metrics row */}
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5">
            <Card>
              <CardContent className="flex flex-col text-left">
                <span className="text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider">
                  Period Income
                </span>
                <span className="text-2xl font-black text-slate-850 dark:text-slate-100 mt-1 text-emerald-650">
                  ₹{totalIncome}
                </span>
                <span className="text-[10px] text-slate-400 mt-1 flex items-center gap-1 font-medium">
                  <TrendingUp className="w-3.5 h-3.5" /> Direct inflows
                </span>
              </CardContent>
            </Card>

            <Card>
              <CardContent className="flex flex-col text-left">
                <span className="text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider">
                  Period Expenses
                </span>
                <span className="text-2xl font-black text-slate-850 dark:text-slate-100 mt-1 text-rose-600">
                  ₹{totalExpense}
                </span>
                <span className="text-[10px] text-slate-400 mt-1 flex items-center gap-1 font-medium">
                  <TrendingDown className="w-3.5 h-3.5" /> Total spent
                </span>
              </CardContent>
            </Card>

            <Card>
              <CardContent className="flex flex-col text-left">
                <span className="text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider">
                  Net Savings
                </span>
                <span className={`text-2xl font-black mt-1 ${netSavings < 0 ? 'text-rose-600' : 'text-emerald-600'}`}>
                  ₹{netSavings}
                </span>
                <span className="text-[10px] text-slate-400 mt-1 font-medium">
                  Remaining net profit
                </span>
              </CardContent>
            </Card>

            <Card>
              <CardContent className="flex flex-col text-left">
                <span className="text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider">
                  Savings Rate Ratio
                </span>
                <span className="text-2xl font-black text-slate-855 dark:text-slate-100 mt-1">
                  {savingsRate}%
                </span>
                <span className="text-[10px] text-slate-400 mt-1 font-medium">
                  Percent of income preserved
                </span>
              </CardContent>
            </Card>
          </div>

          {/* Breakdown columns */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Spending Category chart */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <PieIcon className="w-5 h-5 text-indigo-500" />
                  Category Spending Deficit
                </CardTitle>
              </CardHeader>
              <CardContent className="h-72 flex flex-col justify-between items-center sm:flex-row">
                {chartData.length === 0 ? (
                  <div className="w-full flex items-center justify-center text-sm text-slate-400">
                    No expense records found.
                  </div>
                ) : (
                  <>
                    <div className="w-full sm:w-1/2 h-full">
                      <ResponsiveContainer width="100%" height="100%">
                        <PieChart>
                          <Pie
                            data={chartData}
                            cx="50%"
                            cy="50%"
                            innerRadius={50}
                            outerRadius={70}
                            paddingAngle={3}
                            dataKey="value"
                            nameKey="name"
                          >
                            {chartData.map((entry, index) => (
                              <Cell key={`cell-${index}`} fill={entry.color || COLORS[index % COLORS.length]} />
                            ))}
                          </Pie>
                          <Tooltip formatter={(value: any) => `₹${value}`} />
                        </PieChart>
                      </ResponsiveContainer>
                    </div>
                    <div className="w-full sm:w-1/2 flex flex-col gap-2 text-left overflow-y-auto max-h-[220px] pr-1 mt-4 sm:mt-0">
                      {chartData.map((item, idx) => (
                        <div key={idx} className="flex items-center gap-2 text-xs font-semibold text-slate-655 dark:text-slate-350">
                          <span
                            className="w-2.5 h-2.5 rounded-full shrink-0"
                            style={{ backgroundColor: item.color || COLORS[idx % COLORS.length] }}
                          />
                          <span className="truncate max-w-[100px]">{item.name}</span>
                          <span className="text-slate-400 ml-auto font-medium">₹{item.value}</span>
                        </div>
                      ))}
                    </div>
                  </>
                )}
              </CardContent>
            </Card>

            {/* Account Balances list */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Wallet className="w-5 h-5 text-indigo-500" />
                  Account Asset Statement
                </CardTitle>
              </CardHeader>
              <CardContent className="h-72 overflow-y-auto pr-1">
                {accounts.length === 0 ? (
                  <div className="h-full flex items-center justify-center text-sm text-slate-400">
                    No account records logged.
                  </div>
                ) : (
                  <div className="flex flex-col gap-3">
                    {accounts.map((acc) => (
                      <div key={acc.id} className="flex items-center justify-between p-3.5 bg-slate-50/50 dark:bg-slate-900/40 border border-slate-150/40 dark:border-slate-800/40 rounded-xl">
                        <div className="flex flex-col text-left">
                          <span className="text-xs font-bold text-slate-805 dark:text-slate-205">{acc.name}</span>
                          <span className="text-[9px] uppercase font-bold text-slate-400 mt-0.5 tracking-wider">{acc.account_type}</span>
                        </div>
                        <span className="text-sm font-black text-slate-805 dark:text-slate-50">
                          ₹{acc.balance}
                        </span>
                      </div>
                    ))}
                  </div>
                )}
              </CardContent>
            </Card>
          </div>

          {/* Period Transactions list */}
          <Card>
            <CardHeader>
              <CardTitle>Period Transaction Registry ({transactions.length} records)</CardTitle>
            </CardHeader>
            <CardContent>
              <Table headers={['Date', 'Title', 'Category', 'Account', 'Merchant', 'Type', 'Amount']}>
                {transactions.slice(0, 50).map((tx) => {
                  const accName = accounts.find((a) => a.id === tx.account_id)?.name || `Account #${tx.account_id}`;
                  const cat = categories.find((c) => c.id === tx.category_id);
                  const catName = cat?.name || 'Uncategorized';
                  const catColor = cat?.color || '#94a3b8';

                  const isExpense = tx.transaction_type.toLowerCase() === 'expense';
                  const isIncome = tx.transaction_type.toLowerCase() === 'income';

                  return (
                    <TableRow key={tx.id}>
                      <TableCell className="whitespace-nowrap font-medium text-slate-500">
                        {new Date(tx.transaction_date).toLocaleDateString()}
                      </TableCell>
                      <TableCell className="font-bold text-slate-800 dark:text-slate-200">{tx.title}</TableCell>
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
                    </TableRow>
                  );
                })}
              </Table>
              {transactions.length > 50 && (
                <div className="text-center text-xs text-slate-400 mt-4 font-semibold">
                  Showing first 50 transactions only. Use CSV export to view all.
                </div>
              )}
            </CardContent>
          </Card>
        </div>
      )}

      {/* Printable styles */}
      <style>{`
        @media print {
          body {
            background-color: white !important;
            color: black !important;
          }
          .printable-area {
            padding: 0 !important;
            margin: 0 !important;
          }
          .no-print {
            display: none !important;
          }
          header, sidebar, aside, nav, button {
            display: none !important;
          }
          .glass-card, .glass-nav {
            background: none !important;
            box-shadow: none !important;
            border: none !important;
            backdrop-filter: none !important;
          }
        }
      `}</style>
    </div>
  );
};
export default Reports;
