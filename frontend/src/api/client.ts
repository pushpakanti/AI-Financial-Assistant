import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1';

export const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request Interceptor: Attach JWT Token if available
apiClient.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('auth_token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Response Interceptor: Handle errors globally
apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response) {
      // Unauthorized: Clear token and redirect to login if not already there
      if (error.response.status === 401 && !window.location.pathname.includes('/login')) {
        localStorage.removeItem('auth_token');
        window.dispatchEvent(new Event('auth-expired'));
      }
      return Promise.reject({
        message:
          error.response.data?.message ||
          error.response.data?.errors?.detail ||
          'An error occurred on the server.',
        status: error.response.status,
        data: error.response.data,
      });
    }
    return Promise.reject({
      message: error.message || 'Network error, please check your connection.',
    });
  }
);
export default apiClient;
