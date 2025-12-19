import { createContext, useContext, useState, useEffect } from 'react';
import { getFeatureAccess } from '../config/tiers';

const UserContext = createContext();

export const useUser = () => {
    const context = useContext(UserContext);
    if (!context) {
        throw new Error('useUser must be used within UserProvider');
    }
    return context;
};

/**
 * UserProvider - Manages authentication and tier-based access
 * 
 * Stores API key and user tier in localStorage
 * Provides feature flags based on subscription tier
 */
export const UserProvider = ({ children }) => {
    const [user, setUser] = useState(null);
    const [apiKey, setApiKey] = useState(null);
    const [tier, setTier] = useState('free'); // free, scout_pro, guard_lite, full_stack
    const [loading, setLoading] = useState(true);

    // Load from localStorage on mount
    useEffect(() => {
        const storedApiKey = localStorage.getItem('sentinyl_api_key');
        const storedTier = localStorage.getItem('sentinyl_tier');

        if (storedApiKey) {
            setApiKey(storedApiKey);
        }

        if (storedTier) {
            setTier(storedTier);
        }

        setLoading(false);
    }, []);

    // Get feature access from centralized config
    const featureAccess = getFeatureAccess(tier);

    const login = (newApiKey, newTier) => {
        setApiKey(newApiKey);
        setTier(newTier);
        localStorage.setItem('sentinyl_api_key', newApiKey);
        localStorage.setItem('sentinyl_tier', newTier);
    };

    const logout = () => {
        setApiKey(null);
        setTier('free');
        setUser(null);
        localStorage.removeItem('sentinyl_api_key');
        localStorage.removeItem('sentinyl_tier');
    };

    const updateTier = (newTier) => {
        setTier(newTier);
        localStorage.setItem('sentinyl_tier', newTier);
    };

    const value = {
        user,
        setUser,
        apiKey,
        tier,
        login,
        logout,
        updateTier,
        loading,
        ...featureAccess
    };

    return (
        <UserContext.Provider value={value}>
            {children}
        </UserContext.Provider>
    );
};
