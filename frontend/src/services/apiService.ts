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

const mapTypeToFrontend = (type: string): 'income' | 'expense' | 'transfer' => {
  const lower = type.toLowerCase();
  if (lower === 'income' || lower === 'expense' || lower === 'transfer') {
    return lower;
  }
  return 'expense'; // fallback
};

const mapTransactionToFrontend = (tx: any): Transaction => ({
  ...tx,
  transaction_type: mapTypeToFrontend(tx.transaction_type),
});

const mapTransactionPageToFrontend = (page: any): TransactionPage => ({
  ...page,
  items: page.items.map(mapTransactionToFrontend),
});

const mapRecentTransactionToFrontend = (tx: any): any => {
  if (!tx) return tx;
  return {
    ...tx,
    transaction_type: mapTypeToFrontend(tx.transaction_type),
  };
};

export const apiService = {
  // Dashboard
  getDashboard: async (): Promise<DashboardData> => {
    const response = await apiClient.get<any>('/dashboard');
    const data = response.data;
    if (data.recent_activity) {
      if (data.recent_activity.recent_transactions) {
        data.recent_activity.recent_transactions = data.recent_activity.recent_transactions.map(mapRecentTransactionToFrontend);
      }
      if (data.recent_activity.largest_expense) {
        data.recent_activity.largest_expense = mapRecentTransactionToFrontend(data.recent_activity.largest_expense);
      }
      if (data.recent_activity.largest_income) {
        data.recent_activity.largest_income = mapRecentTransactionToFrontend(data.recent_activity.largest_income);
      }
    }
    return data as DashboardData;
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
    const formattedParams = params ? {
      ...params,
      transaction_type: params.transaction_type ? params.transaction_type.toUpperCase() : undefined
    } : undefined;
    const response = await apiClient.get<any>('/transactions', { params: formattedParams });
    return mapTransactionPageToFrontend(response.data);
  },
  searchTransactions: async (params: { query: string; limit?: number; offset?: number }): Promise<TransactionPage> => {
    const response = await apiClient.get<any>('/transactions/search', { params });
    return mapTransactionPageToFrontend(response.data);
  },
  getTransactionSummary: async (params?: {
    account_id?: number;
    category_id?: number;
    transaction_type?: string;
    start_date?: string;
    end_date?: string;
    merchant?: string;
  }): Promise<TransactionSummary> => {
    const formattedParams = params ? {
      ...params,
      transaction_type: params.transaction_type ? params.transaction_type.toUpperCase() : undefined
    } : undefined;
    const response = await apiClient.get<TransactionSummary>('/transactions/summary', { params: formattedParams });
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
    const formattedData = {
      ...data,
      transaction_type: data.transaction_type.toUpperCase()
    };
    const response = await apiClient.post<any>('/transactions', formattedData);
    return mapTransactionToFrontend(response.data);
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
    const formattedData = {
      ...data,
      transaction_type: data.transaction_type ? data.transaction_type.toUpperCase() : undefined
    };
    const response = await apiClient.put<any>(`/transactions/${id}`, formattedData);
    return mapTransactionToFrontend(response.data);
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

    const response = await apiClient.post<any>('/statements/upload', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
    const data = response.data;
    if (data.preview_transactions) {
      data.preview_transactions = data.preview_transactions.map((tx: any) => ({
        ...tx,
        transaction_type: tx.transaction_type ? mapTypeToFrontend(tx.transaction_type) : null,
      }));
    }
    return data as StatementUploadPreview;
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
