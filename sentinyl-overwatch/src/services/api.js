import axios from 'axios';

const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

// Create axios instance
const api = axios.create({
    baseURL: API_BASE_URL,
    timeout: 10000,
    headers: {
        'Content-Type': 'application/json'
    }
});

// Request interceptor - Add auth token
api.interceptors.request.use(
    (config) => {
        const apiKey = localStorage.getItem('sentinyl_api_key');
        if (apiKey) {
            config.headers.Authorization = `Bearer ${apiKey}`;
        }
        return config;
    },
    (error) => {
        return Promise.reject(error);
    }
);

// Response interceptor - Handle errors globally
api.interceptors.response.use(
    (response) => response,
    (error) => {
        if (error.response) {
            // Handle specific error codes
            switch (error.response.status) {
                case 401:
                    console.error('Unauthorized - Invalid API key');
                    localStorage.removeItem('sentinyl_api_key');
                    window.location.href = '/login';
                    break;
                case 403:
                    console.error('Forbidden - Insufficient permissions');
                    break;
                case 429:
                    console.error('Rate limit exceeded');
                    break;
                default:
                    console.error('API Error:', error.response.data);
            }
        } else if (error.request) {
            console.error('No response from server');
        } else {
            console.error('Request error:', error.message);
        }
        return Promise.reject(error);
    }
);

// ===== AUTH ENDPOINTS =====

export const authAPI = {
    // Get current user + tier
    getMe: async () => {
        const response = await api.get('/auth/me');
        return response.data;
    },

    // Register new user
    register: async (email, name) => {
        const response = await api.post('/auth/register', { email, name });
        return response.data;
    }
};

// ===== SCOUT ENDPOINTS =====

export const scoutAPI = {
    // Start a new scan
    startScan: async (domain, scanType, priority = 'normal') => {
        const response = await api.post('/scan', {
            domain,
            scan_type: scanType,
            priority
        });
        return response.data;
    },

    // Get scan results
    getResults: async (jobId) => {
        const response = await api.get(`/results/${jobId}`);
        return response.data;
    },

    // Get platform statistics
    getStats: async () => {
        const response = await api.get('/stats');
        return response.data;
    },

    // Get recent threats
    getThreats: async (limit = 50) => {
        const response = await api.get('/threats', { params: { limit } });
        return response.data;
    }
};

// ===== GUARD ENDPOINTS =====

export const guardAPI = {
    // Log an alert
    logAlert: async (alertData) => {
        const response = await api.post('/guard/alert', alertData);
        return response.data;
    },

    // Block an IP address
    blockIP: async (ip, reason, agentId) => {
        const response = await api.post('/guard/block-ip', {
            ip_address: ip,
            reason,
            agent_id: agentId
        });
        return response.data;
    },

    // Get monitored agents
    getAgents: async () => {
        const response = await api.get('/guard/agents');
        return response.data;
    },

    // Get alerts
    getAlerts: async (limit = 50) => {
        const response = await api.get('/guard/alerts', { params: { limit } });
        return response.data;
    }
};

// ===== SYSTEM ENDPOINTS =====

export const systemAPI = {
    // Health check
    getHealth: async () => {
        const response = await api.get('/health');
        return response.data;
    }
};

// Export the base axios instance for custom calls
export default api;
