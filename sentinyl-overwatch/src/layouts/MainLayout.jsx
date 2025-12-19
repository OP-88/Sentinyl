import { Link, useLocation } from 'react-router-dom';
import { motion } from 'framer-motion';
import {
    LayoutDashboard,
    Eye,
    Shield,
    Activity,
    Settings,
    LogOut
} from 'lucide-react';
import { useUser } from '../context/UserContext';
import { useTierAccess } from '../hooks/useTierAccess';

/**
 * MainLayout - Shell for SIEM dashboard with navigation
 */
export default function MainLayout({ children }) {
    const location = useLocation();
    const { logout, tierName, tier } = useUser();
    const { hasScout, hasGuard, hasGhost, hasLazarus } = useTierAccess();

    const navItems = [
        {
            path: '/',
            icon: LayoutDashboard,
            label: 'Dashboard',
            show: true
        }
    ];

    const getTierBadgeColor = () => {
        switch (tier) {
            case 'full_stack':
                return 'bg-purple-600 text-white';
            case 'scout_pro':
                return 'bg-blue-600 text-white';
            case 'guard_lite':
                return 'bg-cyan-600 text-white';
            default:
                return 'bg-gray-600 text-white';
        }
    };

    return (
        <div className="min-h-screen bg-gradient-to-br from-slate-950 via-blue-950 to-slate-950">
            {/* Top Navigation */}
            <nav className="bg-slate-900/80 backdrop-blur-lg border-b border-slate-700">
                <div className="max-w-full px-6 py-4">
                    <div className="flex items-center justify-between">
                        {/* Logo */}
                        <div className="flex items-center gap-3">
                            <Shield className="w-8 h-8 text-cyan-400" />
                            <div>
                                <h1 className="text-xl font-bold text-white">SENTINYL</h1>
                                <p className="text-xs text-slate-400">Security Operations Platform</p>
                            </div>
                        </div>

                        {/* User Info */}
                        <div className="flex items-center gap-4">
                            <div className="flex items-center gap-3">
                                <div className="text-right">
                                    <p className="text-sm text-white font-medium">Admin</p>
                                    <span className={`text-xs px-2 py-1 rounded-full ${getTierBadgeColor()}`}>
                                        {tierName}
                                    </span>
                                </div>
                                <Activity className="w-8 h-8 text-green-400" />
                            </div>
                        </div>
                    </div>
                </div>
            </nav>

            <div className="flex h-[calc(100vh-73px)]">
                {/* Sidebar */}
                <aside className="w-64 bg-slate-900/50 backdrop-blur border-r border-slate-700">
                    <nav className="p-4 space-y-2">
                        {navItems
                            .filter(item => item.show)
                            .map((item) => {
                                const Icon = item.icon;
                                const isActive = location.pathname === item.path;

                                return (
                                    <Link
                                        key={item.path}
                                        to={item.path}
                                        className="block"
                                    >
                                        <motion.div
                                            whileHover={{ scale: 1.02, x: 4 }}
                                            whileTap={{ scale: 0.98 }}
                                            className={`flex items-center gap-3 px-4 py-3 rounded-lg transition-all ${isActive
                                                ? 'bg-cyan-600 text-white shadow-lg shadow-cyan-600/30'
                                                : 'text-slate-300 hover:bg-slate-800 hover:text-white'
                                                }`}
                                        >
                                            <Icon className="w-5 h-5" />
                                            <span className="font-medium">{item.label}</span>
                                        </motion.div>
                                    </Link>
                                );
                            })}

                        {/* Settings & Logout */}
                        <div className="pt-4 mt-4 border-t border-slate-700">
                            <button
                                onClick={() => {/* TODO: Settings modal */ }}
                                className="flex items-center gap-3 px-4 py-3 rounded-lg text-slate-300 hover:bg-slate-800 hover:text-white transition-all w-full"
                            >
                                <Settings className="w-5 h-5" />
                                <span className="font-medium">Settings</span>
                            </button>

                            <button
                                onClick={logout}
                                className="flex items-center gap-3 px-4 py-3 rounded-lg text-red-400 hover:bg-red-950 hover:text-red-300 transition-all w-full"
                            >
                                <LogOut className="w-5 h-5" />
                                <span className="font-medium">Logout</span>
                            </button>
                        </div>
                    </nav>

                    {/* System Status */}
                    <div className="absolute bottom-4 left-4 right-4">
                        <div className="bg-slate-800/50 rounded-lg p-3 border border-slate-700">
                            <div className="flex items-center gap-2 mb-2">
                                <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse"></div>
                                <span className="text-xs font-medium text-green-400">SYSTEM ONLINE</span>
                            </div>
                            <p className="text-xs text-slate-400">All services operational</p>
                        </div>
                    </div>
                </aside>

                {/* Main Content */}
                <main className="flex-1 overflow-y-auto">
                    {children}
                </main>
            </div>
        </div>
    );
}
