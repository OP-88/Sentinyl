import { createBrowserRouter, RouterProvider } from 'react-router-dom';
import { UserProvider } from './context/UserContext';
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
        <UserProvider>
            <RouterProvider router={router} />
        </UserProvider>
    );
}
