import { useState } from 'react';
import { motion } from 'framer-motion';
import { Shield, Settings } from 'lucide-react';
import { useUser } from '../context/UserContext';
import SettingsPanel from '../components/SettingsPanel';

/**
 * MainLayout - Simplified header-only layout for SIEM dashboard
 */
export default function MainLayout({ children }) {
    const { tierName, tier } = useUser();
    const [isSettingsOpen, setIsSettingsOpen] = useState(false);

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

                        {/* Right Side: Status, Tier Badge, Settings */}
                        <div className="flex items-center gap-6">
                            {/* System Status Indicator */}
                            <div className="flex items-center gap-2 px-3 py-2 bg-slate-800/50 rounded-lg border border-slate-700">
                                <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse"></div>
                                <span className="text-xs font-medium text-green-400">SYSTEM ONLINE</span>
                            </div>

                            {/* User Info & Tier - Centered */}
                            <div className="text-center">
                                <p className="text-sm text-white font-medium">Admin</p>
                                <span className={`inline-block text-xs px-2 py-1 rounded-full ${getTierBadgeColor()}`}>
                                    {tierName}
                                </span>
                            </div>

                            {/* Settings Button - No Scale Animation */}
                            <button
                                onClick={() => setIsSettingsOpen(true)}
                                className="p-3 bg-slate-800/50 hover:bg-cyan-600/20 rounded-lg border border-slate-700 hover:border-cyan-400 transition-all duration-200 group"
                                title="Settings"
                            >
                                <Settings className="w-5 h-5 text-slate-400 group-hover:text-cyan-300 group-hover:rotate-90 transition-all duration-300" />
                            </button>
                        </div>
                    </div>
                </div>
            </nav>

            {/* Main Content - Full Width */}
            <main className="h-[calc(100vh-73px)] overflow-y-auto">
                {children}
            </main>

            {/* Settings Panel */}
            <SettingsPanel isOpen={isSettingsOpen} onClose={() => setIsSettingsOpen(false)} />
        </div>
    );
}
