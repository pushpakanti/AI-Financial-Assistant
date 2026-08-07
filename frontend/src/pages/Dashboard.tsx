import React from 'react';
import { useQuery } from '@tanstack/react-query';
import { apiService } from '../services/apiService';
import { Card, CardHeader, CardTitle, CardContent } from '../components/ui/Card';
import { Badge } from '../components/ui/Badge';
import { Button } from '../components/ui/Button';
import {
  TrendingUp,
  TrendingDown,
  Wallet,
  PiggyBank,
  ArrowRight,
  Plus,
  Bot,
  Upload,
  AlertTriangle,
  Loader2
} from 'lucide-react';
import { Link, useNavigate } from 'react-router-dom';
import {
  ResponsiveContainer,
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  PieChart,
  Pie,
  Cell,
  BarChart,
  Bar
} from 'recharts';

export const Dashboard: React.FC = () => {
  const navigate = useNavigate();

  const { data: dashboardData, isLoading, error, refetch } = useQuery({
    queryKey: ['dashboard'],
    queryFn: apiService.getDashboard,
  });

  if (isLoading) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[60vh] gap-3">
        <Loader2 className="w-8 h-8 animate-spin text-indigo-650" />
        <span className="text-sm text-slate-500 font-medium">Loading dashboard analytics...</span>
      </div>
    );
  }

  if (error) {
    return (
      <div className="text-center py-12 glass-card rounded-2xl border border-slate-200/50 p-8 max-w-md mx-auto">
        <AlertTriangle className="w-12 h-12 text-rose-500 mx-auto mb-4" />
        <h3 className="text-lg font-bold text-slate-800 dark:text-slate-100">Failed to Load Dashboard</h3>
        <p className="text-sm text-slate-500 mt-2 mb-6">
          {(error as any).message || 'There was an issue fetching dashboard statistics.'}
        </p>
        <Button onClick={() => refetch()} className="mx-auto">
          Retry Loading
        </Button>
      </div>
    );
  }

  const { user_summary, charts, recent_activity, statistics } = dashboardData!;

  // Colors for category pie chart
  const COLORS = ['#4f46e5', '#8b5cf6', '#ec4899', '#f43f5e', '#f59e0b', '#10b981', '#06b6d4', '#3b82f6'];

  const formattedBalance = new Intl.NumberFormat('en-IN', {
    style: 'currency',
    currency: 'INR',
    maximumFractionDigits: 0
  }).format(user_summary.total_balance);

  const formattedIncome = new Intl.NumberFormat('en-IN', {
    style: 'currency',
    currency: 'INR',
    maximumFractionDigits: 0
  }).format(user_summary.monthly_income);

  const formattedExpense = new Intl.NumberFormat('en-IN', {
    style: 'currency',
    currency: 'INR',
    maximumFractionDigits: 0
  }).format(user_summary.monthly_expense);

  return (
    <div className="flex flex-col gap-8">
      {/* Welcome Banner / Overview */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h2 className="text-xl md:text-2xl font-extrabold text-slate-850 dark:text-slate-100 tracking-tight">
            Financial Summary
          </h2>
          <p className="text-sm text-slate-500 dark:text-slate-400 mt-1">
            Here is a breakdown of your personal finances and budget limits.
          </p>
        </div>

        {/* Quick Actions */}
        <div className="flex flex-wrap gap-2">
          <Button
            onClick={() => navigate('/transactions?add=true')}
            leftIcon={<Plus className="w-4 h-4" />}
            size="sm"
          >
            Add Transaction
          </Button>
          <Button
            onClick={() => navigate('/upload')}
            leftIcon={<Upload className="w-4 h-4" />}
            variant="outline"
            size="sm"
          >
            Import Statement
          </Button>
          <Button
            onClick={() => navigate('/chat')}
            leftIcon={<Bot className="w-4 h-4" />}
            variant="secondary"
            size="sm"
          >
            Ask AI Assistant
          </Button>
        </div>
      </div>

      {/* Statistics Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5">
        <Card>
          <CardContent className="flex items-center justify-between">
            <div className="flex flex-col">
              <span className="text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider">
                Total Balance
              </span>
              <span className="text-2xl font-black text-slate-800 dark:text-slate-100 mt-1.5 leading-none">
                {formattedBalance}
              </span>
              <span className="text-[10px] text-slate-400 mt-2 font-medium">
                Across {user_summary.total_accounts} active accounts
              </span>
            </div>
            <div className="p-3 bg-indigo-50 dark:bg-indigo-950/20 text-indigo-600 dark:text-indigo-400 rounded-xl">
              <Wallet className="w-6 h-6" />
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="flex items-center justify-between">
            <div className="flex flex-col">
              <span className="text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider">
                Monthly Income
              </span>
              <span className="text-2xl font-black text-slate-850 dark:text-slate-100 mt-1.5 leading-none">
                {formattedIncome}
              </span>
              <span className="text-[10px] text-emerald-500 flex items-center gap-1 mt-2 font-semibold">
                <TrendingUp className="w-3.5 h-3.5" /> Direct deposits this month
              </span>
            </div>
            <div className="p-3 bg-emerald-50 dark:bg-emerald-950/20 text-emerald-600 dark:text-emerald-400 rounded-xl">
              <TrendingUp className="w-6 h-6" />
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="flex items-center justify-between">
            <div className="flex flex-col">
              <span className="text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider">
                Monthly Expenses
              </span>
              <span className="text-2xl font-black text-slate-850 dark:text-slate-100 mt-1.5 leading-none">
                {formattedExpense}
              </span>
              <span className="text-[10px] text-rose-500 flex items-center gap-1 mt-2 font-semibold">
                <TrendingDown className="w-3.5 h-3.5" /> Total spent this month
              </span>
            </div>
            <div className="p-3 bg-rose-50 dark:bg-rose-950/20 text-rose-600 dark:text-rose-400 rounded-xl">
              <TrendingDown className="w-6 h-6" />
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="flex items-center justify-between">
            <div className="flex flex-col">
              <span className="text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider">
                Active Budgets
              </span>
              <span className="text-2xl font-black text-slate-850 dark:text-slate-100 mt-1.5 leading-none">
                {user_summary.active_budgets}
              </span>
              {user_summary.budget_alerts > 0 ? (
                <span className="text-[10px] text-rose-500 flex items-center gap-1 mt-2 font-semibold">
                  <AlertTriangle className="w-3.5 h-3.5" /> {user_summary.budget_alerts} budget warnings!
                </span>
              ) : (
                <span className="text-[10px] text-slate-400 mt-2 font-medium">
                  All budgets are within limits
                </span>
              )}
            </div>
            <div className="p-3 bg-amber-50 dark:bg-amber-950/20 text-amber-600 dark:text-amber-400 rounded-xl">
              <PiggyBank className="w-6 h-6" />
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Main Charts Row */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Monthly Trend Area Chart */}
        <Card className="lg:col-span-2">
          <CardHeader>
            <CardTitle>Income vs Expenses Trend</CardTitle>
          </CardHeader>
          <CardContent className="h-80">
            {charts.monthly_income_vs_expense.length === 0 ? (
              <div className="h-full flex items-center justify-center text-sm text-slate-400">
                No monthly data available to display trend.
              </div>
            ) : (
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={charts.monthly_income_vs_expense} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                  <defs>
                    <linearGradient id="incomeColor" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#10b981" stopOpacity={0.2}/>
                      <stop offset="95%" stopColor="#10b981" stopOpacity={0}/>
                    </linearGradient>
                    <linearGradient id="expenseColor" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#ef4444" stopOpacity={0.2}/>
                      <stop offset="95%" stopColor="#ef4444" stopOpacity={0}/>
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" className="stroke-slate-200 dark:stroke-slate-800" />
                  <XAxis dataKey="month" className="text-[10px] font-semibold text-slate-450 fill-current" />
                  <YAxis className="text-[10px] font-semibold text-slate-450 fill-current" />
                  <Tooltip
                    contentStyle={{
                      backgroundColor: 'rgba(255, 255, 255, 0.9)',
                      border: 'none',
                      borderRadius: '12px',
                      boxShadow: '0 10px 15px -3px rgba(0, 0, 0, 0.1)',
                      color: '#1e293b'
                    }}
                  />
                  <Legend verticalAlign="top" height={36} wrapperStyle={{ fontSize: '11px', fontWeight: 600 }} />
                  <Area name="Income" type="monotone" dataKey="income" stroke="#10b981" strokeWidth={2} fillOpacity={1} fill="url(#incomeColor)" />
                  <Area name="Expense" type="monotone" dataKey="expense" stroke="#ef4444" strokeWidth={2} fillOpacity={1} fill="url(#expenseColor)" />
                </AreaChart>
              </ResponsiveContainer>
            )}
          </CardContent>
        </Card>

        {/* Expense by Category Pie Chart */}
        <Card>
          <CardHeader>
            <CardTitle>Spending by Category</CardTitle>
          </CardHeader>
          <CardContent className="h-80 flex flex-col justify-between items-center">
            {charts.expense_by_category.length === 0 ? (
              <div className="h-full flex items-center justify-center text-sm text-slate-400">
                No expense category records found.
              </div>
            ) : (
              <>
                <div className="w-full h-[70%]">
                  <ResponsiveContainer width="100%" height="100%">
                    <PieChart>
                      <Pie
                        data={charts.expense_by_category}
                        cx="50%"
                        cy="50%"
                        innerRadius={55}
                        outerRadius={75}
                        paddingAngle={4}
                        dataKey="amount"
                        nameKey="category_name"
                      >
                        {charts.expense_by_category.map((_, index) => (
                          <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                        ))}
                      </Pie>
                      <Tooltip
                        contentStyle={{
                          backgroundColor: 'rgba(255, 255, 255, 0.9)',
                          border: 'none',
                          borderRadius: '12px',
                          boxShadow: '0 10px 15px -3px rgba(0, 0, 0, 0.1)',
                          color: '#1e293b'
                        }}
                        formatter={(value: any) => `₹${value}`}
                      />
                    </PieChart>
                  </ResponsiveContainer>
                </div>
                <div className="w-full grid grid-cols-2 gap-2 text-left mt-3 overflow-y-auto max-h-[90px] pr-1">
                  {charts.expense_by_category.map((item, idx) => (
                    <div key={idx} className="flex items-center gap-1.5 text-[11px] font-semibold text-slate-600 dark:text-slate-400">
                      <span
                        className="w-2.5 h-2.5 rounded-full shrink-0"
                        style={{ backgroundColor: COLORS[idx % COLORS.length] }}
                      />
                      <span className="truncate max-w-[85px]">{item.category_name}</span>
                      <span className="text-[10px] text-slate-400 ml-auto font-medium">
                        {Math.round((item.amount / user_summary.monthly_expense) * 100) || 0}%
                      </span>
                    </div>
                  ))}
                </div>
              </>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Mid Section: Budgets & Merchants */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Budget Progress limits */}
        <Card>
          <CardHeader className="flex flex-row items-center justify-between">
            <CardTitle>Budget Limits</CardTitle>
            <Link to="/budgets" className="text-xs font-bold text-indigo-650 dark:text-indigo-400 hover:underline flex items-center gap-0.5">
              View all <ArrowRight className="w-3.5 h-3.5" />
            </Link>
          </CardHeader>
          <CardContent className="flex flex-col gap-4">
            {charts.budget_progress.length === 0 ? (
              <div className="py-8 text-center text-sm text-slate-400">
                No active budgets set. Set limits in the Budgets tab.
              </div>
            ) : (
              charts.budget_progress.slice(0, 4).map((budget) => {
                const percent = Math.min(100, Math.round(budget.percentage_used));
                const isWarning = budget.status === 'warned';
                const isExceeded = budget.status === 'exceeded';
                
                let progressColor = 'bg-indigo-600';
                if (isWarning) progressColor = 'bg-amber-500';
                if (isExceeded) progressColor = 'bg-rose-500';

                return (
                  <div key={budget.budget_id} className="flex flex-col gap-1.5">
                    <div className="flex items-center justify-between text-xs font-semibold">
                      <span className="text-slate-700 dark:text-slate-350">{budget.name}</span>
                      <span className="text-slate-500">
                        ₹{budget.spent} / <span className="text-slate-400">₹{budget.amount}</span>
                      </span>
                    </div>
                    <div className="w-full h-2 rounded-full bg-slate-100 dark:bg-slate-800 overflow-hidden">
                      <div className={`h-full rounded-full ${progressColor}`} style={{ width: `${percent}%` }} />
                    </div>
                    <div className="flex items-center justify-between text-[10px] text-slate-400 font-medium">
                      <span>{percent}% used</span>
                      {isExceeded ? (
                        <span className="text-rose-500 font-semibold">Exceeded limit!</span>
                      ) : isWarning ? (
                        <span className="text-amber-500 font-semibold">Approaching limit</span>
                      ) : (
                        <span>₹{budget.remaining} remaining</span>
                      )}
                    </div>
                  </div>
                );
              })
            )}
          </CardContent>
        </Card>

        {/* Expense by Merchant Bar Chart */}
        <Card>
          <CardHeader>
            <CardTitle>Spending by Merchant</CardTitle>
          </CardHeader>
          <CardContent className="h-64">
            {charts.expense_by_merchant.length === 0 ? (
              <div className="h-full flex items-center justify-center text-sm text-slate-400">
                No merchant spending recorded.
              </div>
            ) : (
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={charts.expense_by_merchant.slice(0, 5)} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" className="stroke-slate-200 dark:stroke-slate-800" />
                  <XAxis dataKey="merchant" className="text-[10px] font-semibold text-slate-450 fill-current" />
                  <YAxis className="text-[10px] font-semibold text-slate-450 fill-current" />
                  <Tooltip
                    contentStyle={{
                      backgroundColor: 'rgba(255, 255, 255, 0.9)',
                      border: 'none',
                      borderRadius: '12px',
                      boxShadow: '0 10px 15px -3px rgba(0, 0, 0, 0.1)',
                      color: '#1e293b'
                    }}
                    formatter={(value: any) => `₹${value}`}
                  />
                  <Bar name="Spent" dataKey="amount" fill="#6366f1" radius={[4, 4, 0, 0]}>
                    {charts.expense_by_merchant.slice(0, 5).map((_, index) => (
                      <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Bottom Section: Recent Activity & Cash Flow statistics */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Recent Transactions List */}
        <Card className="lg:col-span-2">
          <CardHeader className="flex flex-row items-center justify-between">
            <CardTitle>Recent Transactions</CardTitle>
            <Link to="/transactions" className="text-xs font-bold text-indigo-650 dark:text-indigo-400 hover:underline flex items-center gap-0.5">
              View all <ArrowRight className="w-3.5 h-3.5" />
            </Link>
          </CardHeader>
          <CardContent className="flex flex-col gap-3">
            {recent_activity.recent_transactions.length === 0 ? (
              <div className="py-8 text-center text-sm text-slate-400">
                No recent transactions. Click Add Transaction to log one.
              </div>
            ) : (
              recent_activity.recent_transactions.map((tx) => {
                const isExpense = tx.transaction_type === 'expense';
                const isIncome = tx.transaction_type === 'income';
                
                return (
                  <div key={tx.id} className="flex items-center justify-between p-3 bg-slate-50/50 dark:bg-slate-900/40 border border-slate-100/50 dark:border-slate-800/40 rounded-xl hover:bg-slate-100/50 dark:hover:bg-slate-850/50 transition-colors">
                    <div className="flex items-center gap-3">
                      <div className={`w-9 h-9 rounded-xl flex items-center justify-center font-bold text-sm ${
                        isIncome
                          ? 'bg-emerald-50 text-emerald-650 dark:bg-emerald-950/20'
                          : isExpense
                          ? 'bg-rose-50 text-rose-650 dark:bg-rose-950/20'
                          : 'bg-indigo-50 text-indigo-650 dark:bg-indigo-950/20'
                      }`}>
                        {isIncome ? '+' : isExpense ? '-' : '⇄'}
                      </div>
                      <div className="flex flex-col text-left">
                        <span className="text-sm font-bold text-slate-800 dark:text-slate-200">
                          {tx.title}
                        </span>
                        <span className="text-[10px] text-slate-400 font-medium">
                          {tx.category_name || 'Uncategorized'} • {new Date(tx.transaction_date).toLocaleDateString()}
                        </span>
                      </div>
                    </div>
                    <span className={`text-sm font-black ${
                      isIncome
                        ? 'text-emerald-600'
                        : isExpense
                        ? 'text-rose-600'
                        : 'text-slate-650 dark:text-slate-300'
                    }`}>
                      {isIncome ? '+' : isExpense ? '-' : ''}₹{tx.amount}
                    </span>
                  </div>
                );
              })
            )}
          </CardContent>
        </Card>

        {/* Financial Statistics & Insights */}
        <Card>
          <CardHeader>
            <CardTitle>Analytics Insights</CardTitle>
          </CardHeader>
          <CardContent className="flex flex-col gap-4 text-sm">
            <div className="flex justify-between items-center py-2.5 border-b border-slate-100 dark:border-slate-800">
              <span className="font-semibold text-slate-500 dark:text-slate-400 text-xs">Savings Rate</span>
              <Badge variant="success" className="font-bold">
                {Math.round(statistics.savings_rate * 100)}%
              </Badge>
            </div>
            
            <div className="flex justify-between items-center py-2.5 border-b border-slate-100 dark:border-slate-800">
              <span className="font-semibold text-slate-500 dark:text-slate-400 text-xs">Avg Daily Spending</span>
              <span className="font-bold text-slate-700 dark:text-slate-200">
                ₹{Math.round(statistics.average_daily_expense)}
              </span>
            </div>

            <div className="flex justify-between items-center py-2.5 border-b border-slate-100 dark:border-slate-800">
              <span className="font-semibold text-slate-500 dark:text-slate-400 text-xs">Avg Monthly Spending</span>
              <span className="font-bold text-slate-700 dark:text-slate-200">
                ₹{Math.round(statistics.average_monthly_expense)}
              </span>
            </div>

            {statistics.highest_spending_category && (
              <div className="flex flex-col gap-1 py-2.5 border-b border-slate-100 dark:border-slate-800 text-left">
                <span className="font-semibold text-slate-500 dark:text-slate-400 text-xs">Top Category</span>
                <div className="flex justify-between items-center mt-1">
                  <span className="font-bold text-slate-800 dark:text-slate-250">
                    {statistics.highest_spending_category.category_name}
                  </span>
                  <span className="font-extrabold text-slate-650 dark:text-slate-300">
                    ₹{statistics.highest_spending_category.amount}
                  </span>
                </div>
              </div>
            )}

            {statistics.highest_spending_merchant && (
              <div className="flex flex-col gap-1 py-2.5 text-left">
                <span className="font-semibold text-slate-500 dark:text-slate-400 text-xs">Top Merchant</span>
                <div className="flex justify-between items-center mt-1">
                  <span className="font-bold text-slate-800 dark:text-slate-250">
                    {statistics.highest_spending_merchant.merchant}
                  </span>
                  <span className="font-extrabold text-slate-650 dark:text-slate-300">
                    ₹{statistics.highest_spending_merchant.amount}
                  </span>
                </div>
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
};
export default Dashboard;
