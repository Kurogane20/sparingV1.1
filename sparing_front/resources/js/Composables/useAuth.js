import { ref, computed } from 'vue';
import { useApi } from './useApi';
import axios from 'axios';
import logger from '../Utils/logger';

// Shared authentication state
const user = ref(null);
const token = ref(localStorage.getItem('access_token'));

// Base API URL
const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

// Helper function to decode JWT token
const decodeJWT = (token) => {
  try {
    const base64Url = token.split('.')[1];
    const base64 = base64Url.replace(/-/g, '+').replace(/_/g, '/');
    const jsonPayload = decodeURIComponent(
      atob(base64)
        .split('')
        .map((c) => '%' + ('00' + c.charCodeAt(0).toString(16)).slice(-2))
        .join('')
    );
    return JSON.parse(jsonPayload);
  } catch (error) {
    console.error('Failed to decode JWT:', error);
    return null;
  }
};

export function useAuth() {
  const { login: apiLogin, logout: apiLogout } = useApi();
  const isAuthenticated = computed(() => !!token.value);

  // Initialize user from localStorage
  const initUser = () => {
    const storedUser = localStorage.getItem('user');
    if (storedUser) {
      user.value = JSON.parse(storedUser);
      logger.log('=== INIT USER FROM LOCALSTORAGE ===');
      logger.log('User loaded:', user.value);
      logger.log('User role:', user.value?.role);
      logger.log('User sites:', user.value?.sites);
      logger.log('User sites length:', user.value?.sites?.length);
    } else {
      logger.log('No user found in localStorage');
    }
  };

  // Login function
  const login = async (credentials) => {
    try {
      const response = await apiLogin(credentials);

      logger.log('Login API Response:', response);

      // Store tokens
      token.value = response.access_token;
      localStorage.setItem('access_token', response.access_token);
      localStorage.setItem('refresh_token', response.refresh_token);

      // Decode JWT token to get user info
      const jwtPayload = decodeJWT(response.access_token);
      logger.log('JWT Payload:', jwtPayload);

      // Store user info from API response or JWT
      let userData;

      // CRITICAL: Extract numeric user_id from JWT for database lookups
      // JWT 'sub' field typically contains the numeric user ID
      const numericUserId = jwtPayload ?
        (jwtPayload.user_id || jwtPayload.sub || jwtPayload.id) : null;

      logger.log('Numeric user ID from JWT:', numericUserId);
      logger.log('Numeric user ID type:', typeof numericUserId);

      if (response.user) {
        // If API returns user object (preferred)
        userData = {
          id: numericUserId || response.user.id,
          email: response.user.email || credentials.email,
          name: response.user.name || response.user.username,
          role: response.user.role || 'viewer',
          sites: response.user.sites || [],
        };
      } else if (jwtPayload) {
        // Decode from JWT token
        userData = {
          id: numericUserId,
          email: jwtPayload.email || credentials.email,
          name: jwtPayload.name || jwtPayload.username || credentials.email.split('@')[0],
          role: jwtPayload.role || 'viewer',
          sites: jwtPayload.sites || [],
        };
      } else {
        // Fallback: create from credentials (least privilege)
        userData = {
          id: numericUserId || response.id || null,
          email: response.email || credentials.email,
          name: response.name || credentials.email.split('@')[0],
          role: 'viewer', // Always default to viewer for security
          sites: response.sites || [],
        };
      }

      logger.log('User Data to be stored:', userData);
      logger.log('User role:', userData.role);
      logger.log('User sites array (before fetch):', userData.sites);

      // Fetch site assignments from viewer-sites API if user is not admin
      // NOTE: This requires backend to allow viewer/operator access to /admin/viewer-sites
      // OR backend should include sites in login response/JWT
      if (userData.role === 'viewer' || userData.role === 'operator') {
        try {
          logger.log('=== FETCHING VIEWER-SITES FOR USER ===');
          logger.log('User ID to filter by:', userData.id);
          logger.log('User ID type:', typeof userData.id);
          logger.warn('Viewer role accessing /admin/viewer-sites may return 403');
          logger.warn('Backend needs to allow viewer access or return sites in login response');

          // Fetch viewer-sites and all sites in parallel
          const [viewerSitesResponse, sitesResponse] = await Promise.all([
            axios.get(`${API_BASE_URL}/admin/viewer-sites`, {
              headers: { 'Authorization': `Bearer ${response.access_token}` }
            }),
            axios.get(`${API_BASE_URL}/sites`, {
              headers: { 'Authorization': `Bearer ${response.access_token}` },
              params: { per_page: 100 }  // Fetch up to 100 sites
            })
          ]);

          logger.log('Viewer-Sites API Response:', viewerSitesResponse.data);
          logger.log('Sites API Response:', sitesResponse.data);

          const viewerSites = viewerSitesResponse.data?.viewer_sites || [];
          logger.log('Total viewer-sites entries:', viewerSites.length);
          logger.log('First few viewer-sites entries:', viewerSites.slice(0, 3));

          // Extract sites data (handle different response structures)
          let allSites = [];
          if (sitesResponse.data?.items) {
            allSites = sitesResponse.data.items;
          } else if (Array.isArray(sitesResponse.data)) {
            allSites = sitesResponse.data;
          } else if (sitesResponse.data?.data) {
            allSites = sitesResponse.data.data;
          }

          logger.log('=== SITES API RESPONSE DEBUG ===');
          logger.log('Raw sitesResponse.data:', sitesResponse.data);
          logger.log('Total sites available:', allSites.length);
          logger.log('First site object:', allSites[0]);
          logger.log('Site object keys:', allSites[0] ? Object.keys(allSites[0]) : 'no sites');

          // Create a map of site_id to site_uid for quick lookup
          const siteIdToUidMap = {};
          allSites.forEach((site, index) => {
            // Try different possible field names for numeric ID
            const numericId = site.id || site.site_id || site.siteId;
            const stringUid = site.uid || site.site_uid || site.siteUid;

            if (numericId && stringUid) {
              siteIdToUidMap[numericId] = stringUid;
              logger.log(`Mapped site #${index}: id=${numericId} → uid=${stringUid}`);
            } else {
              logger.warn(`Site #${index} missing fields - id:${numericId}, uid:${stringUid}`, site);
            }
          });

          logger.log('Final Site ID to UID map:', siteIdToUidMap);
          logger.log('Map has entries:', Object.keys(siteIdToUidMap).length);

          // Find all site assignments for this user
          const userSiteIds = viewerSites
            .filter(vs => {
              const matches = vs.user_id === userData.id ||
                vs.user_id === String(userData.id) ||
                vs.user_id === Number(userData.id);
              if (matches) {
                logger.log('Match found - site_id:', vs.site_id, 'site_uid:', vs.site_uid);
              }
              return matches;
            })
            .map(vs => vs.site_id);

          logger.log('User site IDs from viewer_sites table:', userSiteIds);

          // Convert site_ids to site_uids
          const userSiteUids = userSiteIds
            .map(siteId => {
              const uid = siteIdToUidMap[siteId];
              logger.log(`Converting site_id ${siteId} → site_uid ${uid}`);
              return uid;
            })
            .filter(uid => uid !== undefined);

          logger.log('User site UIDs after conversion:', userSiteUids);
          logger.log('Number of sites assigned:', userSiteUids.length);

          // Update user data with fetched site UIDs
          userData.sites = userSiteUids;
        } catch (error) {
          console.error('Failed to fetch viewer-sites on login:', error);
          console.error('Error details:', error.response?.data || error.message);
          console.error('Error status:', error.response?.status);
          // Keep the sites from JWT/response if API call fails
        }
      } else if (userData.role === 'admin') {
        // Admin has access to all sites (empty array or null)
        userData.sites = [];
        logger.log('User is admin - sites set to empty array');
      }

      logger.log('Final user sites array:', userData.sites);
      logger.log('Final userData object:', userData);

      // CRITICAL: Ensure sites is an array before saving
      if (!Array.isArray(userData.sites)) {
        console.error('WARNING: userData.sites is not an array!', userData.sites);
        userData.sites = [];
      }

      user.value = userData;
      localStorage.setItem('user', JSON.stringify(userData));

      // Verify localStorage save
      const storedUser = JSON.parse(localStorage.getItem('user'));
      logger.log('User data saved to localStorage:', storedUser);
      logger.log('Sites in localStorage:', storedUser?.sites);
      logger.log('Sites in localStorage is Array?:', Array.isArray(storedUser?.sites));
      logger.log('Sites in localStorage length:', storedUser?.sites?.length);

      // Double-check reactive state
      logger.log('user.value after save:', user.value);
      logger.log('user.value.sites after save:', user.value?.sites);

      return response;
    } catch (error) {
      throw error;
    }
  };

  // Logout function
  const logout = async () => {
    // Clear local storage first (always clear even if API fails)
    token.value = null;
    user.value = null;
    localStorage.removeItem('access_token');
    localStorage.removeItem('refresh_token');
    localStorage.removeItem('user');

    // Try to call API logout (but don't block if it fails)
    try {
      await apiLogout();
    } catch (error) {
      // Ignore API errors - user is logged out locally anyway
      logger.warn('Logout API call failed (user is still logged out locally):', error.message);
    }
  };

  // Check if user has specific role
  const hasRole = (role) => {
    return user.value?.role === role;
  };

  // Check if user is admin
  const isAdmin = computed(() => hasRole('admin'));

  // Check if user is operator
  const isOperator = computed(() => hasRole('operator') || hasRole('admin'));

  // Check if user is viewer
  const isViewer = computed(() => hasRole('viewer'));

  // Get sites assigned to user (empty array means all sites for admin)
  const getUserSites = computed(() => {
    logger.log('=== GET USER SITES COMPUTED ===');
    logger.log('user.value:', user.value);
    logger.log('user.value.sites:', user.value?.sites);
    logger.log('user.value.sites type:', typeof user.value?.sites);
    logger.log('user.value.sites is Array?:', Array.isArray(user.value?.sites));
    logger.log('user.value.sites length:', user.value?.sites?.length);

    // Admin can see all sites (no filtering)
    if (isAdmin.value) {
      return null; // null indicates no filtering needed
    }
    // For operator and viewer, return assigned sites from viewer_sites table
    // Empty array means user has no site access
    const sites = user.value?.sites || [];
    logger.log('Returning sites:', sites);
    return sites;
  });

  // Filter sites based on user permissions
  const filterSitesByUser = (sites) => {
    logger.log('=== FILTER SITES BY USER ===');
    logger.log('Total sites to filter:', sites.length);
    logger.log('Sites UIDs:', sites.map(s => s.uid));

    const userSites = getUserSites.value;

    logger.log('Current user object:', user.value);
    logger.log('User role:', user.value?.role);
    logger.log('User assigned sites (from getUserSites):', userSites);
    logger.log('User assigned sites type:', typeof userSites);
    logger.log('User assigned sites is Array?:', Array.isArray(userSites));

    // If null (admin), return all sites
    if (userSites === null) {
      logger.log('User is admin - returning all', sites.length, 'sites');
      return sites;
    }
    // If empty array and not admin, user has no assigned sites
    if (userSites.length === 0) {
      logger.warn('User has no assigned sites - returning empty array');
      logger.warn('This means the user.sites array is empty');
      return [];
    }
    // Filter sites by user's assigned site UIDs
    logger.log('Filtering sites...');
    const filtered = sites.filter(site => {
      const included = userSites.includes(site.uid);
      logger.log(`  Site ${site.uid} (${site.name}): ${included ? 'INCLUDED' : 'EXCLUDED'}`);
      return included;
    });
    logger.log('Filtered sites count:', filtered.length);
    logger.log('Filtered sites:', filtered.map(s => ({ uid: s.uid, name: s.name })));
    return filtered;
  };

  // Initialize
  initUser();

  return {
    user,
    token,
    isAuthenticated,
    isAdmin,
    isOperator,
    isViewer,
    getUserSites,
    filterSitesByUser,
    login,
    logout,
    hasRole,
  };
}
