import apiClient from '../api/client';
import type {
  Account,
  Transaction,
  TransactionPage,
  TransactionSummary,
  Budget,
  BudgetProgress,
  BudgetSummary,
  Goal,
  GoalProgress,
  GoalPrediction,
  GoalRecommendation,
  GoalSummaryMetric,
  Category,
  CategoryUsage,
  DashboardData,
  ChatResponse,
  StatementUploadPreview,
  StatementImportResponse,
  Notification,
  NotificationPage
} from '../types';

export const apiService = {
  // Dashboard
  getDashboard: async (): Promise<DashboardData> => {
    const response = await apiClient.get<DashboardData>('/dashboard');
    return response.data;
  },

  // Accounts
  getAccounts: async (): Promise<Account[]> => {
    const response = await apiClient.get<Account[]>('/accounts');
    return response.data;
  },
  createAccount: async (data: { name: string; account_type: string; balance: number; currency: string }): Promise<Account> => {
    const response = await apiClient.post<Account>('/accounts', data);
    return response.data;
  },
  updateAccount: async (id: number, data: Partial<{ name: string; account_type: string; balance: number; currency: string }>): Promise<Account> => {
    const response = await apiClient.put<Account>(`/accounts/${id}`, data);
    return response.data;
  },
  deleteAccount: async (id: number): Promise<void> => {
    await apiClient.delete(`/accounts/${id}`);
  },

  // Categories
  getCategories: async (): Promise<Category[]> => {
    const response = await apiClient.get<Category[]>('/categories');
    return response.data;
  },
  getCustomCategories: async (): Promise<Category[]> => {
    const response = await apiClient.get<Category[]>('/categories/custom');
    return response.data;
  },
  getDefaultCategories: async (): Promise<Category[]> => {
    const response = await apiClient.get<Category[]>('/categories/default');
    return response.data;
  },
  getCategoryUsage: async (): Promise<CategoryUsage[]> => {
    const response = await apiClient.get<CategoryUsage[]>('/categories/usage');
    return response.data;
  },
  createCategory: async (data: { name: string; icon?: string; color?: string }): Promise<Category> => {
    const response = await apiClient.post<Category>('/categories', data);
    return response.data;
  },
  updateCategory: async (id: number, data: Partial<{ name: string; icon: string; color: string; is_active: boolean }>): Promise<Category> => {
    const response = await apiClient.put<Category>(`/categories/${id}`, data);
    return response.data;
  },
  deleteCategory: async (id: number): Promise<void> => {
    await apiClient.delete(`/categories/${id}`);
  },

  // Transactions
  getTransactions: async (params?: {
    account_id?: number;
    category_id?: number;
    transaction_type?: string;
    start_date?: string;
    end_date?: string;
    merchant?: string;
    limit?: number;
    offset?: number;
  }): Promise<TransactionPage> => {
    const response = await apiClient.get<TransactionPage>('/transactions', { params });
    return response.data;
  },
  searchTransactions: async (params: { query: string; limit?: number; offset?: number }): Promise<TransactionPage> => {
    const response = await apiClient.get<TransactionPage>('/transactions/search', { params });
    return response.data;
  },
  getTransactionSummary: async (params?: {
    account_id?: number;
    category_id?: number;
    transaction_type?: string;
    start_date?: string;
    end_date?: string;
    merchant?: string;
  }): Promise<TransactionSummary> => {
    const response = await apiClient.get<TransactionSummary>('/transactions/summary', { params });
    return response.data;
  },
  createTransaction: async (data: {
    account_id: number;
    category_id?: number;
    transaction_type: string;
    title: string;
    description?: string;
    amount: number;
    transaction_date: string;
    merchant?: string;
    payment_method?: string;
    location?: string;
    tags?: string[];
    receipt_url?: string;
  }): Promise<Transaction> => {
    const response = await apiClient.post<Transaction>('/transactions', data);
    return response.data;
  },
  updateTransaction: async (id: number, data: Partial<{
    account_id: number;
    category_id: number | null;
    transaction_type: string;
    title: string;
    description: string | null;
    amount: number;
    transaction_date: string;
    merchant: string | null;
    payment_method: string | null;
    location: string | null;
    tags: string[];
    receipt_url: string | null;
  }>): Promise<Transaction> => {
    const response = await apiClient.put<Transaction>(`/transactions/${id}`, data);
    return response.data;
  },
  deleteTransaction: async (id: number): Promise<void> => {
    await apiClient.delete(`/transactions/${id}`);
  },

  // Budgets
  // Budgets
  getBudgets: async (): Promise<Budget[]> => {
    const response = await apiClient.get<Budget[]>('/budgets');
    return response.data;
  },

  getBudgetProgress: async (): Promise<BudgetProgress[]> => {
    const response = await apiClient.get<BudgetProgress[]>('/budgets/progress');
    return response.data;
  },

  getBudgetSummary: async (): Promise<BudgetSummary> => {
    const response = await apiClient.get<BudgetSummary>('/budgets/summary');
    return response.data;
  },

  getBudgetAlerts: async (): Promise<BudgetProgress[]> => {
    const response = await apiClient.get<BudgetProgress[]>('/budgets/alerts');
    return response.data;
  },

  createBudget: async (data: {
    name: string;
    category_id: number | null;
    budget_type: 'MONTHLY' | 'WEEKLY' | 'YEARLY' | 'CUSTOM';
    amount: number;
    start_date: string;
    end_date: string;
    alert_percentage: number;
  }): Promise<Budget> => {
    const response = await apiClient.post<Budget>('/budgets', data);
    return response.data;
  },

  updateBudget: async (id: number, data: Partial<{
    name: string;
    category_id: number | null;
    budget_type: 'MONTHLY' | 'WEEKLY' | 'YEARLY' | 'CUSTOM';
    amount: number;
    start_date: string;
    end_date: string;
    alert_percentage: number;
  }>): Promise<Budget> => {
    const response = await apiClient.put<Budget>(`/budgets/${id}`, data);
    return response.data;
  },

  deleteBudget: async (id: number): Promise<void> => {
    await apiClient.delete(`/budgets/${id}`);
  },

  // Goals
  getGoals: async (): Promise<Goal[]> => {
    const response = await apiClient.get<Goal[]>('/goals');
    return response.data;
  },
  getGoalSummary: async (): Promise<GoalSummaryMetric> => {
    const response = await apiClient.get<GoalSummaryMetric>('/goals/summary');
    return response.data;
  },
  getGoalProgress: async (): Promise<GoalProgress[]> => {
    const response = await apiClient.get<GoalProgress[]>('/goals/progress');
    return response.data;
  },
  getGoalPredictions: async (): Promise<GoalPrediction[]> => {
    const response = await apiClient.get<GoalPrediction[]>('/goals/prediction');
    return response.data;
  },
  getGoalRecommendations: async (): Promise<GoalRecommendation[]> => {
    const response = await apiClient.get<GoalRecommendation[]>('/goals/recommendations');
    return response.data;
  },
  createGoal: async (data: {
    title: string;
    target_amount: number;
    current_amount?: number;
    deadline: string;
    priority?: string;
  }): Promise<Goal> => {
    const response = await apiClient.post<Goal>('/goals', data);
    return response.data;
  },
  updateGoal: async (id: number, data: Partial<{
    title: string;
    target_amount: number;
    current_amount: number;
    deadline: string;
    priority: string;
  }>): Promise<Goal> => {
    const response = await apiClient.put<Goal>(`/goals/${id}`, data);
    return response.data;
  },
  deleteGoal: async (id: number): Promise<void> => {
    await apiClient.delete(`/goals/${id}`);
  },

  // Statements Upload
  uploadStatement: async (accountId: number, file: File): Promise<StatementUploadPreview> => {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('account_id', accountId.toString());

    const response = await apiClient.post<StatementUploadPreview>('/statements/upload', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
    return response.data;
  },
  importStatement: async (statementId: number): Promise<StatementImportResponse> => {
    const response = await apiClient.post<StatementImportResponse>(`/statements/${statementId}/import`);
    return response.data;
  },

  // Chat
  sendChatMessage: async (message: string): Promise<ChatResponse> => {
    const response = await apiClient.post<ChatResponse>('/chat', { message });
    return response.data;
  },

  // Notifications
  getNotifications: async (params?: {
    is_read?: boolean;
    notification_type?: string;
    limit?: number;
    offset?: number;
  }): Promise<NotificationPage> => {
    const response = await apiClient.get<NotificationPage>('/notifications', { params });
    return response.data;
  },
  getUnreadNotificationsCount: async (): Promise<{ unread_count: number }> => {
    const response = await apiClient.get<{ unread_count: number }>('/notifications/unread-count');
    return response.data;
  },
  markNotificationRead: async (id: number): Promise<Notification> => {
    const response = await apiClient.patch<Notification>(`/notifications/${id}/read`);
    return response.data;
  },
  markNotificationUnread: async (id: number): Promise<Notification> => {
    const response = await apiClient.patch<Notification>(`/notifications/${id}/unread`);
    return response.data;
  },
  deleteNotification: async (id: number): Promise<void> => {
    await apiClient.delete(`/notifications/${id}`);
  },
};
