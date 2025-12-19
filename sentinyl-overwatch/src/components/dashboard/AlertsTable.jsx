import { motion } from 'framer-motion';
import { AlertCircle, CheckCircle, XCircle, Clock, ExternalLink } from 'lucide-react';
import { useState } from 'react';

/**
 * AlertsTable - Recent security alerts/events table
 * 
 * Displays paginated list of threats and security events
 * with sorting, filtering, and row actions
 */
export default function AlertsTable({ alerts = [] }) {
    const [currentPage, setCurrentPage] = useState(1);
    const itemsPerPage = 10;

    // Mock data for demo
    const mockAlerts = alerts.length > 0 ? alerts : [
        {
            id: 1,
            timestamp: Date.now() - 3600000,
            type: 'Typosquat',
            severity: 'HIGH',
            source: 'exampl3.com',
            status: 'unacknowledged',
            description: 'Malicious domain detected'
        },
        {
            id: 2,
            timestamp: Date.now() - 7200000,
            type: 'GitHub Leak',
            severity: 'CRITICAL',
            source: 'user/repo',
            status: 'acknowledged',
            description: 'API key exposed in commit'
        },
        {
            id: 3,
            timestamp: Date.now() - 10800000,
            type: 'Guard Alert',
            severity: 'MEDIUM',
            source: '185.220.101.1',
            status: 'blocked',
            description: 'Suspicious connection from Russia'
        }
    ];

    const getSeverityColor = (severity) => {
        const colors = {
            CRITICAL: 'bg-red-500/20 text-red-300 border-red-500/50',
            HIGH: 'bg-orange-500/20 text-orange-300 border-orange-500/50',
            MEDIUM: 'bg-yellow-500/20 text-yellow-300 border-yellow-500/50',
            LOW: 'bg-blue-500/20 text-blue-300 border-blue-500/50'
        };
        return colors[severity] || colors.LOW;
    };

    const getStatusIcon = (status) => {
        switch (status) {
            case 'acknowledged':
                return <CheckCircle className="w-4 h-4 text-green-400" />;
            case 'blocked':
                return <XCircle className="w-4 h-4 text-red-400" />;
            default:
                return <Clock className="w-4 h-4 text-yellow-400" />;
        }
    };

    const formatTime = (timestamp) => {
        const date = new Date(timestamp);
        return date.toLocaleString('en-US', {
            month: 'short',
            day: 'numeric',
            hour: '2-digit',
            minute: '2-digit'
        });
    };

    const totalPages = Math.ceil(mockAlerts.length / itemsPerPage);
    const startIndex = (currentPage - 1) * itemsPerPage;
    const paginatedAlerts = mockAlerts.slice(startIndex, startIndex + itemsPerPage);

    return (
        <div className="bg-slate-800/50 backdrop-blur border border-slate-700 rounded-xl overflow-hidden">
            {/* Header */}
            <div className="px-6 py-4 border-b border-slate-700">
                <div className="flex items-center justify-between">
                    <h2 className="text-xl font-bold text-white">Recent Alerts</h2>
                    <div className="flex items-center gap-2">
                        <AlertCircle className="w-5 h-5 text-slate-400" />
                        <span className="text-sm text-slate-400">{mockAlerts.length} total</span>
                    </div>
                </div>
            </div>

            {/* Table */}
            <div className="overflow-x-auto">
                <table className="w-full">
                    <thead className="bg-slate-900/50">
                        <tr>
                            <th className="px-6 py-3 text-left text-xs font-medium text-slate-400 uppercase tracking-wider">
                                Time
                            </th>
                            <th className="px-6 py-3 text-left text-xs font-medium text-slate-400 uppercase tracking-wider">
                                Type
                            </th>
                            <th className="px-6 py-3 text-left text-xs font-medium text-slate-400 uppercase tracking-wider">
                                Severity
                            </th>
                            <th className="px-6 py-3 text-left text-xs font-medium text-slate-400 uppercase tracking-wider">
                                Source
                            </th>
                            <th className="px-6 py-3 text-left text-xs font-medium text-slate-400 uppercase tracking-wider">
                                Description
                            </th>
                            <th className="px-6 py-3 text-left text-xs font-medium text-slate-400 uppercase tracking-wider">
                                Status
                            </th>
                            <th className="px-6 py-3 text-right text-xs font-medium text-slate-400 uppercase tracking-wider">
                                Actions
                            </th>
                        </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-700/50">
                        {paginatedAlerts.map((alert, index) => (
                            <motion.tr
                                key={alert.id}
                                initial={{ opacity: 0, x: -20 }}
                                animate={{ opacity: 1, x: 0 }}
                                transition={{ delay: index * 0.03 }}
                                className="hover:bg-slate-700/30 transition-colors"
                            >
                                <td className="px-6 py-4 whitespace-nowrap text-sm text-slate-300">
                                    {formatTime(alert.timestamp)}
                                </td>
                                <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-white">
                                    {alert.type}
                                </td>
                                <td className="px-6 py-4 whitespace-nowrap">
                                    <span className={`px-2 py-1 text-xs font-semibold rounded-full border ${getSeverityColor(alert.severity)}`}>
                                        {alert.severity}
                                    </span>
                                </td>
                                <td className="px-6 py-4 whitespace-nowrap text-sm text-cyan-400 font-mono">
                                    {alert.source}
                                </td>
                                <td className="px-6 py-4 text-sm text-slate-400">
                                    {alert.description}
                                </td>
                                <td className="px-6 py-4 whitespace-nowrap">
                                    <div className="flex items-center gap-2">
                                        {getStatusIcon(alert.status)}
                                        <span className="text-xs text-slate-400 capitalize">{alert.status}</span>
                                    </div>
                                </td>
                                <td className="px-6 py-4 whitespace-nowrap text-right text-sm">
                                    <button className="text-cyan-400 hover:text-cyan-300 transition-colors">
                                        <ExternalLink className="w-4 h-4" />
                                    </button>
                                </td>
                            </motion.tr>
                        ))}
                    </tbody>
                </table>
            </div>

            {/* Pagination */}
            <div className="px-6 py-4 border-t border-slate-700 flex items-center justify-between">
                <div className="text-sm text-slate-400">
                    Showing {startIndex + 1}-{Math.min(startIndex + itemsPerPage, mockAlerts.length)} of {mockAlerts.length}
                </div>
                <div className="flex gap-2">
                    <button
                        onClick={() => setCurrentPage(p => Math.max(1, p - 1))}
                        disabled={currentPage === 1}
                        className="px-3 py-1 rounded bg-slate-700 text-white text-sm disabled:opacity-50 disabled:cursor-not-allowed hover:bg-slate-600 transition-colors"
                    >
                        Previous
                    </button>
                    <button
                        onClick={() => setCurrentPage(p => Math.min(totalPages, p + 1))}
                        disabled={currentPage === totalPages}
                        className="px-3 py-1 rounded bg-slate-700 text-white text-sm disabled:opacity-50 disabled:cursor-not-allowed hover:bg-slate-600 transition-colors"
                    >
                        Next
                    </button>
                </div>
            </div>
        </div>
    );
}
