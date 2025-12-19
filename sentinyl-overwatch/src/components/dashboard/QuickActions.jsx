import { motion } from 'framer-motion';
import { Play, StopCircle, Download, Eye, Shield, Search } from 'lucide-react';
import { useTierAccess } from '../../hooks/useTierAccess';

/**
 * QuickActions - Action buttons panel
 * 
 * Tier-gated action buttons for quick access to key features
 */
export default function QuickActions({ onStartScan, onOpenOverwatch }) {
    const { hasScout, hasGuard } = useTierAccess();

    const actions = [
        {
            icon: Search,
            label: 'Typosquat Scan',
            description: 'Scan for domain variations',
            color: 'blue',
            show: hasScout,
            onClick: () => onStartScan?.('typosquat')
        },
        {
            icon: Search,
            label: 'GitHub Leak Scan',
            description: 'Search for exposed credentials',
            color: 'purple',
            show: hasScout,
            onClick: () => onStartScan?.('leak')
        },
        {
            icon: Shield,
            label: 'Block IP',
            description: 'Add IP to blocklist',
            color: 'red',
            show: hasGuard,
            onClick: () => alert('Block IP modal - TODO')
        },
        {
            icon: Eye,
            label: 'View Overwatch',
            description: 'Real-time event stream',
            color: 'cyan',
            show: hasGuard,
            onClick: onOpenOverwatch
        },
        {
            icon: Download,
            label: 'Export Data',
            description: 'Download reports',
            color: 'green',
            show: true,
            onClick: () => alert('Export data - TODO')
        }
    ];

    const getColorClasses = (color) => {
        const colors = {
            blue: 'from-blue-500/20 to-blue-600/20 border-blue-500/30 hover:border-blue-400 text-blue-300',
            purple: 'from-purple-500/20 to-purple-600/20 border-purple-500/30 hover:border-purple-400 text-purple-300',
            red: 'from-red-500/20 to-red-600/20 border-red-500/30 hover:border-red-400 text-red-300',
            cyan: 'from-cyan-500/20 to-cyan-600/20 border-cyan-500/30 hover:border-cyan-400 text-cyan-300',
            green: 'from-green-500/20 to-green-600/20 border-green-500/30 hover:border-green-400 text-green-300'
        };
        return colors[color] || colors.blue;
    };

    return (
        <div className="bg-slate-800/50 backdrop-blur border border-slate-700 rounded-xl p-6">
            <div className="flex items-center justify-between mb-4">
                <h2 className="text-xl font-bold text-white">Quick Actions</h2>
                <Play className="w-5 h-5 text-slate-400" />
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
                {actions
                    .filter(action => action.show)
                    .map((action, index) => {
                        const Icon = action.icon;

                        return (
                            <motion.div
                                key={action.label}
                                initial={{ opacity: 0, scale: 0.9 }}
                                animate={{ opacity: 1, scale: 1 }}
                                transition={{ delay: index * 0.05 }}
                                whileHover={{ scale: 1.02 }}
                                whileTap={{ scale: 0.98 }}
                                onClick={action.onClick}
                                className={`bg-gradient-to-br ${getColorClasses(action.color)} border rounded-lg p-4 cursor-pointer transition-all`}
                            >
                                <div className="flex items-start gap-3">
                                    <div className="p-2 bg-slate-900/50 rounded-lg">
                                        <Icon className="w-5 h-5" />
                                    </div>
                                    <div className="flex-1">
                                        <h3 className="font-semibold text-white mb-1">{action.label}</h3>
                                        <p className="text-xs text-slate-400">{action.description}</p>
                                    </div>
                                </div>
                            </motion.div>
                        );
                    })}
            </div>

            {actions.filter(a => a.show).length === 0 && (
                <div className="text-center py-8">
                    <p className="text-slate-400 text-sm">No actions available for your tier</p>
                    <p className="text-xs text-slate-500 mt-1">Upgrade to unlock more features</p>
                </div>
            )}
        </div>
    );
}
