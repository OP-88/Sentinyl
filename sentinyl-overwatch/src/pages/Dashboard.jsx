import { useState } from 'react';
import { motion } from 'framer-motion';
import { Shield, Activity, AlertTriangle, TrendingUp } from 'lucide-react';
import { useTierAccess } from '../hooks/useTierAccess';
import { useApiOnMount, useApi } from '../hooks/useApi';
import { useToast } from '../context/ToastContext';
import { scoutAPI, guardAPI, systemAPI } from '../services/api';
import QuickActions from '../components/dashboard/QuickActions';
import AlertsTable from '../components/dashboard/AlertsTable';
import ThreatChart from '../components/dashboard/ThreatChart';
import SeverityPieChart from '../components/dashboard/SeverityPieChart';
import OverwatchDrawer from '../components/OverwatchDrawer';
import BlockIPModal from '../components/modals/BlockIPModal';
import ExportDataModal from '../components/modals/ExportDataModal';

/**
 * Main SIEM Dashboard - Corporate cybersecurity interface
 * 
 * Shows overview cards, recent alerts, charts, and quick actions
 * Features are tier-gated based on subscription
 */
export default function Dashboard() {
    const { hasScout, hasGuard, tier } = useTierAccess();
    const toast = useToast();
    const [isOverwatchOpen, setIsOverwatchOpen] = useState(false);
    const [isBlockIPModalOpen, setIsBlockIPModalOpen] = useState(false);
    const [isExportModalOpen, setIsExportModalOpen] = useState(false);

    // Fetch platform stats on mount
    const { data: stats, loading: statsLoading, error: statsError, refetch: refetchStats } = useApiOnMount(
        scoutAPI.getStats,
        [],
        { showErrorToast: false } // Handle error display manually
    );

    // API hooks for actions
    const { execute: startScan, loading: scanLoading } = useApi(scoutAPI.startScan, {
        showSuccessToast: true,
        successMessage: 'Scan started successfully'
    });

    const { execute: blockIP, loading: blockIPLoading } = useApi(guardAPI.blockIP, {
        showSuccessToast: true,
        successMessage: 'IP blocked successfully'
    });

    const { execute: exportData, loading: exportLoading } = useApi(systemAPI.exportData, {
        showSuccessToast: true,
        successMessage: 'Data exported successfully'
    });

    const handleStartScan = async (scanType) => {
        try {
            // Prompt for domain
            const domain = prompt('Enter domain to scan:');
            if (!domain) return;

            await startScan(domain, scanType, 'normal');
            refetchStats(); // Refresh stats after starting scan
        } catch (error) {
            // Error already handled by useApi hook
            console.error('Scan error:', error);
        }
    };

    const handleOpenOverwatch = () => {
        setIsOverwatchOpen(true);
    };

    const handleBlockIP = async (ipData) => {
        try {
            // Determine agent_id (in real scenario, this would come from user selection)
            const agentId = 'default-agent-id'; // TODO: Get from context or user selection

            await blockIP(ipData.ip, ipData.reason || 'Manual block from dashboard', agentId);
            setIsBlockIPModalOpen(false);
        } catch (error) {
            console.error('Block IP error:', error);
            throw error; // Re-throw to let modal handle it
        }
    };

    const handleExportData = async (exportConfig) => {
        try {
            const data = await exportData(
                exportConfig.exportType,
                exportConfig.format,
                exportConfig.dateRange
            );

            // Create and trigger download
            const blob = new Blob(
                [typeof data === 'string' ? data : JSON.stringify(data, null, 2)],
                { type: exportConfig.format === 'csv' ? 'text/csv' : 'application/json' }
            );
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `sentinyl-${exportConfig.exportType}-${Date.now()}.${exportConfig.format}`;
            a.click();
            URL.revokeObjectURL(url);

            setIsExportModalOpen(false);
        } catch (error) {
            console.error('Export error:', error);
            throw error;
        }
    };


    return (
        <>
            <div className="p-6 space-y-6">
                {/* Header */}
                <div>
                    <h1 className="text-3xl font-bold text-white mb-2">Security Operations Dashboard</h1>
                    <p className="text-slate-400">Real-time threat monitoring and incident response</p>
                </div>

                {/* Stats Loading Error State */}
                {statsError && !statsLoading && (
                    <div className="bg-red-500/10 border border-red-500/50 rounded-xl p-4 text-center">
                        <p className="text-red-400">Failed to load statistics. </p>
                        <button
                            onClick={refetchStats}
                            className="mt-2 px-4 py-2 bg-red-500 hover:bg-red-600 text-white rounded-lg transition-colors text-sm"
                        >
                            Retry
                        </button>
                    </div>
                )}

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
                                <span className="text-sm text-slate-400">Total</span>
                            </div>
                            {statsLoading ? (
                                <div className="animate-pulse">
                                    <div className="h-8 bg-slate-700 rounded w-20 mb-1"></div>
                                    <div className="h-4 bg-slate-700 rounded w-24"></div>
                                </div>
                            ) : (
                                <>
                                    <h3 className="text-2xl font-bold text-white mb-1">
                                        {stats?.active_threats || 0}
                                    </h3>
                                    <p className="text-sm text-slate-400">Active Threats</p>
                                </>
                            )}
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
                            {statsLoading ? (
                                <div className="animate-pulse">
                                    <div className="h-8 bg-slate-700 rounded w-20 mb-1"></div>
                                    <div className="h-4 bg-slate-700 rounded w-24"></div>
                                </div>
                            ) : (
                                <>
                                    <h3 className="text-2xl font-bold text-white mb-1">
                                        {stats?.pending_scans || 0}
                                    </h3>
                                    <p className="text-sm text-slate-400">Running Scans</p>
                                </>
                            )}
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
                                <span className="text-sm text-slate-400">Protected</span>
                            </div>
                            {statsLoading ? (
                                <div className="animate-pulse">
                                    <div className="h-8 bg-slate-700 rounded w-20 mb-1"></div>
                                    <div className="h-4 bg-slate-700 rounded w-24"></div>
                                </div>
                            ) : (
                                <>
                                    <h3 className="text-2xl font-bold text-white mb-1">
                                        {stats?.total_domains || 0}
                                    </h3>
                                    <p className="text-sm text-slate-400">Domains Monitored</p>
                                </>
                            )}
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
                <QuickActions
                    onStartScan={handleStartScan}
                    onOpenOverwatch={handleOpenOverwatch}
                    onBlockIP={() => setIsBlockIPModalOpen(true)}
                    onExportData={() => setIsExportModalOpen(true)}
                />

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

            {/* Block IP Modal */}
            <BlockIPModal
                isOpen={isBlockIPModalOpen}
                onClose={() => setIsBlockIPModalOpen(false)}
                onBlock={handleBlockIP}
            />

            {/* Export Data Modal */}
            <ExportDataModal
                isOpen={isExportModalOpen}
                onClose={() => setIsExportModalOpen(false)}
                onExport={handleExportData}
            />
        </>
    );
}
