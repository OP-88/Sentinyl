import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { X, Download, Check } from 'lucide-react';

/**
 * ExportDataModal - Modal for exporting security reports
 */
export default function ExportDataModal({ isOpen, onClose, onExport }) {
    const [exportType, setExportType] = useState('alerts');
    const [format, setFormat] = useState('json');
    const [dateRange, setDateRange] = useState('7d');
    const [loading, setLoading] = useState(false);

    const handleExport = async () => {
        setLoading(true);
        try {
            await onExport?.({ exportType, format, dateRange });

            // Show success feedback
            setTimeout(() => {
                setLoading(false);
                onClose();
            }, 1500);
        } catch (err) {
            setLoading(false);
            alert('Export failed: ' + err.message);
        }
    };

    if (!isOpen) return null;

    return (
        <AnimatePresence>
            {isOpen && (
                <>
                    {/* Backdrop */}
                    <motion.div
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        exit={{ opacity: 0 }}
                        onClick={onClose}
                        className="fixed inset-0 bg-black/60 backdrop-blur-sm z-50"
                    />

                    {/* Modal */}
                    <div className="fixed inset-0 flex items-center justify-center z-50 p-4">
                        <motion.div
                            initial={{ scale: 0.95, opacity: 0 }}
                            animate={{ scale: 1, opacity: 1 }}
                            exit={{ scale: 0.95, opacity: 0 }}
                            className="bg-slate-900 border border-green-500/30 rounded-xl shadow-2xl max-w-md w-full"
                        >
                            {/* Header */}
                            <div className="flex items-center justify-between p-6 border-b border-slate-700">
                                <div className="flex items-center gap-3">
                                    <div className="p-2 bg-green-500/20 rounded-lg">
                                        <Download className="w-6 h-6 text-green-400" />
                                    </div>
                                    <h2 className="text-xl font-bold text-white">Export Data</h2>
                                </div>
                                <button
                                    onClick={onClose}
                                    className="p-2 hover:bg-slate-800 rounded-lg transition-colors"
                                >
                                    <X className="w-5 h-5 text-slate-400" />
                                </button>
                            </div>

                            {/* Body */}
                            <div className="p-6 space-y-4">
                                {/* Data Type */}
                                <div>
                                    <label className="block text-sm font-medium text-slate-300 mb-2">
                                        Data Type
                                    </label>
                                    <select
                                        value={exportType}
                                        onChange={(e) => setExportType(e.target.value)}
                                        className="w-full bg-slate-950 border border-slate-700 rounded-lg px-4 py-2 text-white focus:outline-none focus:border-green-500 transition-colors"
                                    >
                                        <option value="alerts">Security Alerts</option>
                                        <option value="scans">Scan Results</option>
                                        <option value="blocklist">Blocked IPs</option>
                                        <option value="events">System Events</option>
                                        <option value="all">All Data</option>
                                    </select>
                                </div>

                                {/* Format */}
                                <div>
                                    <label className="block text-sm font-medium text-slate-300 mb-2">
                                        Export Format
                                    </label>
                                    <div className="grid grid-cols-3 gap-2">
                                        <button
                                            onClick={() => setFormat('json')}
                                            className={`px-4 py-2 rounded-lg font-medium transition-colors ${format === 'json'
                                                    ? 'bg-green-600 text-white'
                                                    : 'bg-slate-800 text-slate-300 hover:bg-slate-700'
                                                }`}
                                        >
                                            JSON
                                        </button>
                                        <button
                                            onClick={() => setFormat('csv')}
                                            className={`px-4 py-2 rounded-lg font-medium transition-colors ${format === 'csv'
                                                    ? 'bg-green-600 text-white'
                                                    : 'bg-slate-800 text-slate-300 hover:bg-slate-700'
                                                }`}
                                        >
                                            CSV
                                        </button>
                                        <button
                                            onClick={() => setFormat('pdf')}
                                            className={`px-4 py-2 rounded-lg font-medium transition-colors ${format === 'pdf'
                                                    ? 'bg-green-600 text-white'
                                                    : 'bg-slate-800 text-slate-300 hover:bg-slate-700'
                                                }`}
                                        >
                                            PDF
                                        </button>
                                    </div>
                                </div>

                                {/* Date Range */}
                                <div>
                                    <label className="block text-sm font-medium text-slate-300 mb-2">
                                        Date Range
                                    </label>
                                    <select
                                        value={dateRange}
                                        onChange={(e) => setDateRange(e.target.value)}
                                        className="w-full bg-slate-950 border border-slate-700 rounded-lg px-4 py-2 text-white focus:outline-none focus:border-green-500 transition-colors"
                                    >
                                        <option value="24h">Last 24 Hours</option>
                                        <option value="7d">Last 7 Days</option>
                                        <option value="30d">Last 30 Days</option>
                                        <option value="90d">Last 90 Days</option>
                                        <option value="all">All Time</option>
                                    </select>
                                </div>
                            </div>

                            {/* Footer */}
                            <div className="flex items-center justify-end gap-3 p-6 border-t border-slate-700">
                                <button
                                    onClick={onClose}
                                    disabled={loading}
                                    className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-white rounded-lg transition-colors disabled:opacity-50"
                                >
                                    Cancel
                                </button>
                                <button
                                    onClick={handleExport}
                                    disabled={loading}
                                    className="px-4 py-2 bg-green-600 hover:bg-green-700 text-white rounded-lg transition-colors disabled:opacity-50 flex items-center gap-2"
                                >
                                    {loading ? (
                                        <>
                                            <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                                            Exporting...
                                        </>
                                    ) : (
                                        <>
                                            <Download className="w-4 h-4" />
                                            Export
                                        </>
                                    )}
                                </button>
                            </div>
                        </motion.div>
                    </div>
                </>
            )}
        </AnimatePresence>
    );
}
