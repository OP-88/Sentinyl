import React from 'react';
import { AlertTriangle } from 'lucide-react';

/**
 * Error Boundary - Catches React rendering errors
 * 
 * Prevents entire app from crashing due to component errors
 */
class ErrorBoundary extends React.Component {
    constructor(props) {
        super(props);
        this.state = { hasError: false, error: null, errorInfo: null };
    }

    static getDerivedStateFromError(error) {
        return { hasError: true };
    }

    componentDidCatch(error, errorInfo) {
        console.error('ErrorBoundary caught an error:', error, errorInfo);
        this.setState({
            error,
            errorInfo
        });
    }

    render() {
        if (this.state.hasError) {
            return (
                <div className="min-h-screen bg-slate-950 flex items-center justify-center p-6">
                    <div className="max-w-md w-full bg-slate-800/50 backdrop-blur border border-slate-700 rounded-xl p-8 text-center">
                        <div className="w-16 h-16 bg-red-500/20 rounded-full flex items-center justify-center mx-auto mb-4">
                            <AlertTriangle className="w-8 h-8 text-red-400" />
                        </div>
                        <h2 className="text-2xl font-bold text-white mb-2">Something went wrong</h2>
                        <p className="text-slate-400 mb-6">
                            An unexpected error occurred. Please refresh the page to continue.
                        </p>

                        {process.env.NODE_ENV === 'development' && this.state.error && (
                            <details className="text-left mb-4">
                                <summary className="text-sm text-slate-500 cursor-pointer hover:text-slate-400 mb-2">
                                    Error details
                                </summary>
                                <div className="bg-slate-900 rounded-lg p-4 text-xs font-mono text-red-400 overflow-auto max-h-48">
                                    <p className="mb-2">{this.state.error.toString()}</p>
                                    <pre className="text-slate-500 whitespace-pre-wrap">
                                        {this.state.errorInfo?.componentStack}
                                    </pre>
                                </div>
                            </details>
                        )}

                        <button
                            onClick={() => window.location.reload()}
                            className="px-6 py-2 bg-blue-500 hover:bg-blue-600 text-white rounded-lg transition-colors"
                        >
                            Refresh Page
                        </button>
                    </div>
                </div>
            );
        }

        return this.props.children;
    }
}

export default ErrorBoundary;
