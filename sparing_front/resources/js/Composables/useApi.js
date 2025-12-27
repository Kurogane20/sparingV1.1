import axios from 'axios';
import { ref } from 'vue';
import logger from '../Utils/logger';

// Base API configuration
const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

// Create axios instance with default config
const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor to attach JWT token
apiClient.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('access_token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Response interceptor to handle errors globally
apiClient.interceptors.response.use(
  (response) => response,
  async (error) => {
    if (error.response?.status === 401) {
      // Token expired or invalid - try to refresh
      const refreshToken = localStorage.getItem('refresh_token');
      if (refreshToken) {
        try {
          const { data } = await axios.post(`${API_BASE_URL}/auth/refresh`, {
            refresh_token: refreshToken,
          });
          localStorage.setItem('access_token', data.access_token);
          localStorage.setItem('refresh_token', data.refresh_token);

          // Retry the original request
          error.config.headers.Authorization = `Bearer ${data.access_token}`;
          return apiClient.request(error.config);
        } catch (refreshError) {
          // Refresh failed - redirect to login
          localStorage.removeItem('access_token');
          localStorage.removeItem('refresh_token');
          window.location.href = '/login';
        }
      } else {
        // No refresh token - redirect to login
        window.location.href = '/login';
      }
    } else if (error.response?.status === 403) {
      // Forbidden - user doesn't have access to this resource
      logger.warn('Access denied (403):', error.config.url);
      logger.warn('User may not have permission to access this site/device');
      // Let the error propagate so individual components can handle it
    }
    return Promise.reject(error);
  }
);

export function useApi() {
  const loading = ref(false);
  const error = ref(null);

  // Generic API request wrapper
  const request = async (method, url, data = null, config = {}) => {
    loading.value = true;
    error.value = null;

    try {
      const response = await apiClient({
        method,
        url,
        data,
        ...config,
      });
      return response.data;
    } catch (err) {
      error.value = err.response?.data?.detail || 'An error occurred';
      throw err;
    } finally {
      loading.value = false;
    }
  };

  // Authentication endpoints
  const login = (credentials) => request('POST', '/auth/login', credentials);
  const logout = () => request('POST', '/auth/logout');
  const refreshToken = (token) => request('POST', '/auth/refresh', { refresh_token: token });

  // Health check endpoints
  const healthCheck = () => request('GET', '/healthz');
  const readinessCheck = () => request('GET', '/readyz');

  // Sites endpoints
  const getSites = (params = {}) => request('GET', '/sites', null, { params });
  const getSite = (uid) => request('GET', `/sites/${uid}`);
  const createSite = (data) => request('POST', '/sites', data);
  const updateSite = (uid, data) => request('PATCH', `/sites/${uid}`, data);
  const deleteSite = (uid) => request('DELETE', `/sites/${uid}`);
  const getSiteStats = (uid) => request('GET', `/sites/${uid}/stats/last-seen`);
  const getSiteMetrics = (uid, params = {}) => request('GET', `/sites/${uid}/metrics`, null, { params });

  // Devices endpoints
  const getDevices = (params = {}) => request('GET', '/devices', null, { params });
  const createDevice = (data) => request('POST', '/devices', data);
  const updateDevice = (id, data) => request('PATCH', `/devices/${id}`, data);
  const deleteDevice = (id) => request('DELETE', `/devices/${id}`);

  // Data ingestion endpoints
  const ingestData = (data, idempotencyKey = null) => {
    const config = idempotencyKey ? { headers: { 'Idempotency-Key': idempotencyKey } } : {};
    return request('POST', '/ingest/state', data, config);
  };
  const bulkIngest = (data) => request('POST', '/ingest/bulk', data);

  // Data retrieval endpoints
  const getData = (params = {}) => request('GET', '/data', null, { params });
  const getLatestData = (siteUid) => request('GET', '/data/last', null, { params: { site_uid: siteUid } });

  // Admin endpoints
  const registerUser = (data) => request('POST', '/auth/register', data);
  const getUsers = () => request('GET', '/admin/users');
  const updateUser = (userId, data) => request('PATCH', `/admin/users/${userId}`, data);
  const deleteUser = (userId) => request('DELETE', `/admin/users/${userId}`);

  // Viewer-Sites Management (according to API.md)
  const getViewerSites = () => request('GET', '/admin/viewer-sites');

  const assignViewerToSite = (userId, siteUid) =>
    request('POST', '/admin/viewer-sites', { user_id: userId, site_uid: siteUid });

  const unassignViewerFromSite = (userId, siteUid) =>
    request('DELETE', '/admin/viewer-sites', { user_id: userId, site_uid: siteUid });

  // Update user sites - use the correct viewer-sites endpoints
  const updateUserSites = async (userId, siteUids) => {
    try {
      // First, get current assignments for this user
      const currentAssignments = await getViewerSites();

      // Extract site UIDs currently assigned to this user
      let userCurrentSites = [];
      if (currentAssignments && currentAssignments.viewer_sites) {
        userCurrentSites = currentAssignments.viewer_sites
          .filter(vs => vs.user_id === userId)
          .map(vs => vs.site_uid || vs.site_id);
      }

      logger.log('Current sites for user:', userCurrentSites);
      logger.log('New sites to assign:', siteUids);

      // Determine which sites to add and which to remove
      const sitesToAdd = siteUids.filter(uid => !userCurrentSites.includes(uid));
      const sitesToRemove = userCurrentSites.filter(uid => !siteUids.includes(uid));

      logger.log('Sites to add:', sitesToAdd);
      logger.log('Sites to remove:', sitesToRemove);

      // Remove unassigned sites
      for (const siteUid of sitesToRemove) {
        logger.log(`Removing site ${siteUid} from user ${userId}`);
        await unassignViewerFromSite(userId, siteUid);
      }

      // Add new sites
      for (const siteUid of sitesToAdd) {
        logger.log(`Adding site ${siteUid} to user ${userId}`);
        await assignViewerToSite(userId, siteUid);
      }

      return { success: true, added: sitesToAdd.length, removed: sitesToRemove.length };
    } catch (error) {
      console.error('Failed to update user sites:', error);
      throw error;
    }
  };

  return {
    loading,
    error,
    request,
    // Auth
    login,
    logout,
    refreshToken,
    // Health
    healthCheck,
    readinessCheck,
    // Sites
    getSites,
    getSite,
    createSite,
    updateSite,
    deleteSite,
    getSiteStats,
    getSiteMetrics,
    // Devices
    getDevices,
    createDevice,
    updateDevice,
    deleteDevice,
    // Data
    ingestData,
    bulkIngest,
    getData,
    getLatestData,
    // Admin
    registerUser,
    getUsers,
    updateUser,
    deleteUser,
    getViewerSites,
    assignViewerToSite,
    unassignViewerFromSite,
    updateUserSites,
  };
}
