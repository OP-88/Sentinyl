import { Outlet } from 'react-router-dom';
import MainLayout from '../layouts/MainLayout';

/**
 * Root component with layout wrapper
 */
export default function Root() {
    return (
        <MainLayout>
            <Outlet />
        </MainLayout>
    );
}
