import axios from 'axios';

const rawBase = (process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000').replace(/\/+$/, '');
export const BASE_API_URL = rawBase.endsWith('/api/v1') ? rawBase.slice(0, -7) : rawBase;

export const getApiUrl = (path: string) => {
  const cleanPath = path.startsWith('/') ? path : `/${path}`;
  return `${BASE_API_URL}/api/v1${cleanPath}`;
};

export const apiClient = axios.create({
  baseURL: `${BASE_API_URL}/api/v1`,
  headers: {
    'Content-Type': 'application/json',
  },
});

apiClient.interceptors.request.use((config) => {
  if (typeof window !== 'undefined') {
    const token = localStorage.getItem('access_token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    // Set start time for performance tracking
    (config as any).metadata = { startTime: new Date().getTime() };
  }
  return config;
});

apiClient.interceptors.response.use(
  (response) => {
    if (typeof window !== 'undefined' && (response.config as any).metadata) {
      const duration = new Date().getTime() - (response.config as any).metadata.startTime;
      console.debug(`[Perf] API Latency [${response.config.method?.toUpperCase()} ${response.config.url}]: ${duration}ms`);
    }
    return response;
  },
  async (error) => {
    if (typeof window !== 'undefined' && error.config && (error.config as any).metadata) {
      const duration = new Date().getTime() - (error.config as any).metadata.startTime;
      console.debug(`[Perf] API Latency [ERROR ${error.config.method?.toUpperCase()} ${error.config.url}]: ${duration}ms`);
    }

    if (error.response?.status === 401 && typeof window !== 'undefined') {
      localStorage.removeItem('access_token');
      if (window.location.pathname !== '/login' && window.location.pathname !== '/register') {
        window.location.href = '/login';
      }
    }
    return Promise.reject(error);
  }
);
