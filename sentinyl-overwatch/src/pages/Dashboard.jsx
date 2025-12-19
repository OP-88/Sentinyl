import { useState } from 'react';
import { motion } from 'framer-motion';
import { Shield, Activity, AlertTriangle, TrendingUp } from 'lucide-react';
import { useTierAccess } from '../hooks/useTierAccess';
import QuickActions from '../components/dashboard/QuickActions';
import AlertsTable from '../components/dashboard/AlertsTable';
import ThreatChart from '../components/dashboard/ThreatChart';
import SeverityPieChart from '../components/dashboard/SeverityPieChart';
import OverwatchDrawer from '../components/OverwatchDrawer';

/**
 * Main SIEM Dashboard - Corporate cybersecurity interface
 * 
 * Shows overview cards, recent alerts, charts, and quick actions
 * Features are tier-gated based on subscription
 */
export default function Dashboard() {
    const { hasScout, hasGuard, tier } = useTierAccess();
    const [isOverwatchOpen, setIsOverwatchOpen] = useState(false);

    const handleStartScan = (scanType) => {
        // TODO: Implement scan start logic with API
        console.log('Starting scan:', scanType);
        alert(`Starting ${scanType} scan...\nThis will connect to the FastAPI backend.`);
    };

    const handleOpenOverwatch = () => {
        setIsOverwatchOpen(true);
    };

    return (
        <>
            <div className="p-6 space-y-6">
                {/* Header */}
                <div>
                    <h1 className="text-3xl font-bold text-white mb-2">Security Operations Dashboard</h1>
                    <p className="text-slate-400">Real-time threat monitoring and incident response</p>
                </div>

                {/* Overview Cards */}
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
                    {/* Only show Scout metrics if user has Scout access */}
                    {hasScout && (
                        <motion.div
                            initial={{ opacity: 0, y: 20 }}
                            animate={{ opacity: 1, y: 0 }}
                            className="bg-slate-800/50 backdrop-blur border border-slate-700 rounded-xl p-6"
                        >
                            <div className="flex items-center justify-between mb-4">
                                <div className="p-3 bg-red-500/20 rounded-lg">
                                    <AlertTriangle className="w-6 h-6 text-red-400" />
                                </div>
                                <span className="text-sm text-slate-400">Last 24h</span>
                            </div>
                            <h3 className="text-2xl font-bold text-white mb-1">247</h3>
                            <p className="text-sm text-slate-400">Total Threats</p>
                            <div className="mt-3 flex items-center gap-2">
                                <TrendingUp className="w-4 h-4 text-green-400" />
                                <span className="text-xs text-green-400">+12% from yesterday</span>
                            </div>
                        </motion.div>
                    )}

                    {hasScout && (
                        <motion.div
                            initial={{ opacity: 0, y: 20 }}
                            animate={{ opacity: 1, y: 0 }}
                            transition={{ delay: 0.1 }}
                            className="bg-slate-800/50 backdrop-blur border border-slate-700 rounded-xl p-6"
                        >
                            <div className="flex items-center justify-between mb-4">
                                <div className="p-3 bg-blue-500/20 rounded-lg">
                                    <Activity className="w-6 h-6 text-blue-400" />
                                </div>
                                <span className="text-sm text-slate-400">Active</span>
                            </div>
                            <h3 className="text-2xl font-bold text-white mb-1">3</h3>
                            <p className="text-sm text-slate-400">Running Scans</p>
                        </motion.div>
                    )}

                    {hasGuard && (
                        <motion.div
                            initial={{ opacity: 0, y: 20 }}
                            animate={{ opacity: 1, y: 0 }}
                            transition={{ delay: 0.2 }}
                            className="bg-slate-800/50 backdrop-blur border border-slate-700 rounded-xl p-6"
                        >
                            <div className="flex items-center justify-between mb-4">
                                <div className="p-3 bg-purple-500/20 rounded-lg">
                                    <Shield className="w-6 h-6 text-purple-400" />
                                </div>
                                <span className="text-sm text-slate-400">Blocked</span>
                            </div>
                            <h3 className="text-2xl font-bold text-white mb-1">42</h3>
                            <p className="text-sm text-slate-400">IPs Blocked</p>
                        </motion.div>
                    )}

                    <motion.div
                        initial={{ opacity: 0, y: 20 }}
                        animate={{ opacity: 1, y: 0 }}
                        transition={{ delay: 0.3 }}
                        className="bg-slate-800/50 backdrop-blur border border-slate-700 rounded-xl p-6"
                    >
                        <div className="flex items-center justify-between mb-4">
                            <div className="p-3 bg-green-500/20 rounded-lg">
                                <Activity className="w-6 h-6 text-green-400" />
                            </div>
                            <span className="text-sm text-slate-400">Status</span>
                        </div>
                        <h3 className="text-2xl font-bold text-white mb-1">Healthy</h3>
                        <p className="text-sm text-slate-400">System Health</p>
                    </motion.div>
                </div>

                {/* Quick Actions */}
                <QuickActions onStartScan={handleStartScan} onOpenOverwatch={handleOpenOverwatch} />

                {/* Charts Row */}
                {hasScout && (
                    <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                        <ThreatChart />
                        <SeverityPieChart />
                    </div>
                )}

                {/* Recent Alerts Table */}
                {(hasScout || hasGuard) && (
                    <AlertsTable />
                )}

                {/* No features message for free tier */}
                {tier === 'free' && (
                    <div className="bg-slate-800/50 backdrop-blur border border-slate-700 rounded-xl p-8 text-center">
                        <Shield className="w-16 h-16 text-slate-600 mx-auto mb-4" />
                        <h3 className="text-xl font-bold text-white mb-2">Limited Access</h3>
                        <p className="text-slate-400 mb-4">
                            You're on the Free tier with limited features.
                        </p>
                        <p className="text-sm text-slate-500">
                            Upgrade to Scout Pro, Guard Lite, or Full Stack to unlock powerful security features.
                        </p>
                    </div>
                )}
            </div>

            {/* Overwatch Drawer */}
            <OverwatchDrawer isOpen={isOverwatchOpen} onClose={() => setIsOverwatchOpen(false)} />
        </>
    );
}
