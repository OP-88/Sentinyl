import { useState, useEffect, useCallback } from 'react';
import { useToast } from '../context/ToastContext';

/**
 * useApi Hook - Simplified API call management
 * 
 * Handles loading states, errors, and success notifications
 * Includes automatic retry logic with exponential backoff
 * 
 * @param {Function} apiFunc - The API function to call
 * @param {Object} options - Configuration options
 * @returns {Object} - { data, loading, error, execute, reset }
 */
export function useApi(apiFunc, options = {}) {
    const {
        onSuccess = null,
        onError = null,
        showSuccessToast = false,
        showErrorToast = true,
        successMessage = 'Operation completed successfully',
        retries = 3,
        retryDelay = 1000
    } = options;

    const [data, setData] = useState(null);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState(null);
    const toast = useToast();

    const execute = useCallback(async (...args) => {
        setLoading(true);
        setError(null);

        let lastError = null;

        // Retry logic with exponential backoff
        for (let attempt = 0; attempt <= retries; attempt++) {
            try {
                const result = await apiFunc(...args);
                setData(result);
                setLoading(false);

                if (showSuccessToast) {
                    toast.success(successMessage);
                }

                if (onSuccess) {
                    onSuccess(result);
                }

                return result;

            } catch (err) {
                lastError = err;

                // Don't retry on client errors (4xx)
                if (err.response && err.response.status >= 400 && err.response.status < 500) {
                    break;
                }

                // Wait before retry (exponential backoff)
                if (attempt < retries) {
                    await new Promise(resolve =>
                        setTimeout(resolve, retryDelay * Math.pow(2, attempt))
                    );
                }
            }
        }

        // All retries failed
        const errorMessage = getErrorMessage(lastError);
        setError(errorMessage);
        setLoading(false);

        if (showErrorToast) {
            toast.error(errorMessage);
        }

        if (onError) {
            onError(lastError);
        }

        throw lastError;

    }, [apiFunc, onSuccess, onError, showSuccessToast, showErrorToast, successMessage, retries, retryDelay, toast]);

    const reset = useCallback(() => {
        setData(null);
        setLoading(false);
        setError(null);
    }, []);

    return { data, loading, error, execute, reset };
}

/**
 * useApiOnMount Hook - Automatically execute API call on component mount
 * 
 * @param {Function} apiFunc - The API function to call
 * @param {Array} deps - Dependencies array for re-fetching
 * @param {Object} options - Configuration options
 * @returns {Object} - { data, loading, error, refetch }
 */
export function useApiOnMount(apiFunc, deps = [], options = {}) {
    const { data, loading, error, execute } = useApi(apiFunc, {
        ...options,
        showErrorToast: options.showErrorToast ?? true
    });

    const [initialLoad, setInitialLoad] = useState(true);

    useEffect(() => {
        execute().finally(() => {
            if (initialLoad) setInitialLoad(false);
        });
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, deps);

    return {
        data,
        loading: initialLoad ? loading : false, // Only show loading on initial load
        error,
        refetch: execute
    };
}

/**
 * Extract user-friendly error message from error object
 */
function getErrorMessage(error) {
    if (!error) return 'An unknown error occurred';

    // Network errors
    if (error.message === 'Network Error' || !error.response) {
        return 'Unable to connect to server. Please check your internet connection.';
    }

    // API error responses
    if (error.response) {
        const { status, data } = error.response;

        switch (status) {
            case 400:
                return data?.detail || 'Invalid request. Please check your input.';
            case 401:
                return 'Authentication failed. Please log in again.';
            case 403:
                return 'You do not have permission to perform this action.';
            case 404:
                return data?.detail || 'The requested resource was not found.';
            case 429:
                return 'Too many requests. Please try again later.';
            case 500:
                return 'Server error. Please try again later.';
            case 503:
                return 'Service temporarily unavailable. Please try again later.';
            default:
                return data?.detail || data?.message || `Error: ${status}`;
        }
    }

    // Timeout errors
    if (error.code === 'ECONNABORTED') {
        return 'Request timed out. Please try again.';
    }

    return error.message || 'An unexpected error occurred';
}
