export type TransactionType = 'income' | 'expense' | 'transfer';
export type BudgetStatus = 'active' | 'warned' | 'exceeded' | 'expired';
export type GoalPriority = 'LOW' | 'MEDIUM' | 'HIGH';
export type GoalStatus = 'IN_PROGRESS' | 'COMPLETED' | 'OVERDUE';
export type StatementStatus = 'pending' | 'imported' | 'failed';

export interface User {
  id: number;
  full_name: string;
  email: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface Account {
  id: number;
  name: string;
  account_type: string;
  balance: number;
  currency: string;
  created_at: string;
  updated_at: string;
}

export interface Category {
  id: number;
  name: string;
  icon: string | null;
  color: string | null;
  is_default: boolean;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface CategoryUsage extends Category {
  transaction_count: number;
}

export interface Transaction {
  id: number;
  account_id: number;
  category_id: number | null;
  transaction_type: TransactionType;
  title: string;
  description: string | null;
  amount: number;
  transaction_date: string;
  merchant: string | null;
  payment_method: string | null;
  location: string | null;
  tags: string[];
  receipt_url: string | null;
  created_at: string;
  updated_at: string;
}

export interface TransactionPage {
  items: Transaction[];
  total: number;
  limit: number;
  offset: number;
}

export interface TransactionSummary {
  transaction_count: number;
  total_income: number;
  total_expense: number;
  total_transfer: number;
  net_cash_flow: number;
}

export interface Budget {
  id: number;
  name: string;
  category_id: number | null;
  budget_type: 'MONTHLY' | 'WEEKLY' | 'YEARLY' | 'CUSTOM';
  amount: number;
  category_name?: string;
  start_date: string;
  end_date: string;
  alert_percentage: number;
  created_at: string;
  updated_at: string;
}

export interface BudgetProgress extends Budget {
  spent: number;
  remaining: number;
  percentage_used: number;
  status: BudgetStatus;
}

export interface BudgetSummary {
  budget_count: number;
  active_budget_count: number;
  total_budgeted: number;
  total_spent: number;
  total_remaining: number;
}

export interface Goal {
  id: number;
  title: string;
  target_amount: number;
  current_amount: number;
  deadline: string;
  priority: GoalPriority;
  status: GoalStatus;
  monthly_required: number;
  created_at: string;
  updated_at: string;
}

export interface GoalProgress extends Goal {
  remaining_amount: number;
  percentage_complete: number;
  days_remaining: number;
}

export interface GoalPrediction {
  goal_id: number;
  projected_completion_date: string | null;
  required_monthly_contribution: number;
  remaining_amount: number;
  status: GoalStatus;
  prediction_basis: string;
}

export interface GoalRecommendation {
  goal_id: number;
  priority: GoalPriority;
  status: GoalStatus;
  recommendations: string[];
}

export interface GoalSummaryMetric {
  total_goals: number;
  active_goals: number;
  completed_goals: number;
  overdue_goals: number;
  total_target_amount: number;
  total_current_amount: number;
  total_remaining_amount: number;
  overall_completion_percentage: number;
}

// Dashboard structures
export interface UserSummary {
  total_accounts: number;
  total_balance: number;
  monthly_income: number;
  monthly_expense: number;
  net_cash_flow: number;
  total_transactions: number;
  active_budgets: number;
  budget_alerts: number;
}

export interface MonthlyCashFlowPoint {
  month: string;
  income: number;
  expense: number;
}

export interface ExpenseByCategoryPoint {
  category_id: number | null;
  category_name: string;
  amount: number;
}

export interface ExpenseByMerchantPoint {
  merchant: string;
  amount: number;
}

export interface DailySpendingPoint {
  date: string;
  amount: number;
}

export interface BudgetProgressPoint {
  budget_id: number;
  name: string;
  category_id: number | null;
  amount: number;
  spent: number;
  remaining: number;
  percentage_used: number;
  alert_percentage: number;
  status: BudgetStatus;
  end_date: string;
}

export interface DashboardCharts {
  monthly_income_vs_expense: MonthlyCashFlowPoint[];
  expense_by_category: ExpenseByCategoryPoint[];
  expense_by_merchant: ExpenseByMerchantPoint[];
  daily_spending: DailySpendingPoint[];
  budget_progress: BudgetProgressPoint[];
}

export interface RecentTransaction {
  id: number;
  title: string;
  amount: number;
  transaction_type: TransactionType;
  transaction_date: string;
  category_name: string | null;
  merchant: string | null;
  created_at: string;
}

export interface DashboardActivity {
  recent_transactions: RecentTransaction[];
  upcoming_budget_alerts: BudgetProgressPoint[];
  largest_expense: RecentTransaction | null;
  largest_income: RecentTransaction | null;
}

export interface DashboardStatistics {
  average_daily_expense: number;
  average_monthly_expense: number;
  highest_spending_category: ExpenseByCategoryPoint | null;
  highest_spending_merchant: ExpenseByMerchantPoint | null;
  savings_rate: number;
}

export interface DashboardData {
  user_summary: UserSummary;
  charts: DashboardCharts;
  recent_activity: DashboardActivity;
  statistics: DashboardStatistics;
}

// Chat structures
export interface AgentOutput {
  agent: string;
  status: 'planned' | 'completed' | 'skipped';
  summary: string;
  data: Record<string, any>;
}

export interface ChatResponse {
  message: string;
  planned_agents: string[];
  planner: AgentOutput;
  finance: AgentOutput;
  budget: AgentOutput;
  goal: AgentOutput;
  report: AgentOutput;
  memory: AgentOutput;
  tool_results: Array<Record<string, any>>;
}

export interface ChatMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: Date;
  metadata?: ChatResponse;
}

// Statement structures
export interface StatementPreviewTransaction {
  row_number: number;
  date: string | null;
  merchant: string | null;
  description: string | null;
  amount: number | null;
  transaction_type: TransactionType | null;
  category: string | null;
  duplicate: boolean;
  valid: boolean;
  error: string | null;
}

export interface StatementUploadPreview {
  statement_id: number;
  total_rows: number;
  valid_rows: number;
  invalid_rows: number;
  duplicate_rows: number;
  preview_transactions: StatementPreviewTransaction[];
  warnings: string[];
}

export interface StatementImportResponse {
  statement_id: number;
  status: StatementStatus;
  imported_transactions: number;
  skipped_duplicates: number;
}

// Notification structures
export interface Notification {
  id: number;
  title: string;
  message: string;
  notification_type: 'budget_alert' | 'system' | 'goal_alert';
  is_read: boolean;
  created_at: string;
}

export interface NotificationPage {
  items: Notification[];
  total: number;
  limit: number;
  offset: number;
}
