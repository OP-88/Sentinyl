import { createBrowserRouter, RouterProvider } from 'react-router-dom';
import { UserProvider } from './context/UserContext';
import { ToastProvider } from './context/ToastContext';
import ErrorBoundary from './components/ErrorBoundary';
import Root from './pages/Root';
import Dashboard from './pages/Dashboard';
import Overwatch from './pages/Overwatch';

/**
 * Main App - Router configuration
 * 
 * Provides routing and user context to entire application
 */

const router = createBrowserRouter([
    {
        path: '/',
        element: <Root />,
        children: [
            {
                index: true,
                element: <Dashboard />
            },
            {
                path: 'overwatch',
                element: <Overwatch />
            }
        ]
    }
]);

export default function App() {
    return (
        <ErrorBoundary>
            <ToastProvider>
                <UserProvider>
                    <RouterProvider router={router} />
                </UserProvider>
            </ToastProvider>
        </ErrorBoundary>
    );
}

