import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { X, Shield, AlertCircle } from 'lucide-react';

/**
 * BlockIPModal - Modal for blocking IP addresses
 */
export default function BlockIPModal({ isOpen, onClose, onBlock }) {
    const [ipAddress, setIpAddress] = useState('');
    const [reason, setReason] = useState('');
    const [duration, setDuration] = useState('permanent');
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState('');

    const validateIP = (ip) => {
        const ipv4Regex = /^(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$/;
        return ipv4Regex.test(ip);
    };

    const handleSubmit = async () => {
        setError('');

        if (!ipAddress.trim()) {
            setError('IP address is required');
            return;
        }

        if (!validateIP(ipAddress)) {
            setError('Invalid IP address format');
            return;
        }

        setLoading(true);
        try {
            // Call the onBlock handler with IP data
            await onBlock?.({ ip: ipAddress, reason, duration });

            // Reset form
            setIpAddress('');
            setReason('');
            setDuration('permanent');
            onClose();
        } catch (err) {
            setError(err.message || 'Failed to block IP');
        } finally {
            setLoading(false);
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
                            className="bg-slate-900 border border-red-500/30 rounded-xl shadow-2xl max-w-md w-full"
                        >
                            {/* Header */}
                            <div className="flex items-center justify-between p-6 border-b border-slate-700">
                                <div className="flex items-center gap-3">
                                    <div className="p-2 bg-red-500/20 rounded-lg">
                                        <Shield className="w-6 h-6 text-red-400" />
                                    </div>
                                    <h2 className="text-xl font-bold text-white">Block IP Address</h2>
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
                                {/* IP Address Input */}
                                <div>
                                    <label className="block text-sm font-medium text-slate-300 mb-2">
                                        IP Address *
                                    </label>
                                    <input
                                        type="text"
                                        value={ipAddress}
                                        onChange={(e) => setIpAddress(e.target.value)}
                                        placeholder="e.g., 192.168.1.100"
                                        className="w-full bg-slate-950 border border-slate-700 rounded-lg px-4 py-2 text-white focus:outline-none focus:border-red-500 transition-colors"
                                    />
                                </div>

                                {/* Reason Input */}
                                <div>
                                    <label className="block text-sm font-medium text-slate-300 mb-2">
                                        Reason (Optional)
                                    </label>
                                    <textarea
                                        value={reason}
                                        onChange={(e) => setReason(e.target.value)}
                                        placeholder="Why is this IP being blocked?"
                                        rows={3}
                                        className="w-full bg-slate-950 border border-slate-700 rounded-lg px-4 py-2 text-white focus:outline-none focus:border-red-500 transition-colors resize-none"
                                    />
                                </div>

                                {/* Duration */}
                                <div>
                                    <label className="block text-sm font-medium text-slate-300 mb-2">
                                        Duration
                                    </label>
                                    <select
                                        value={duration}
                                        onChange={(e) => setDuration(e.target.value)}
                                        className="w-full bg-slate-950 border border-slate-700 rounded-lg px-4 py-2 text-white focus:outline-none focus:border-red-500 transition-colors"
                                    >
                                        <option value="1h">1 Hour</option>
                                        <option value="24h">24 Hours</option>
                                        <option value="7d">7 Days</option>
                                        <option value="30d">30 Days</option>
                                        <option value="permanent">Permanent</option>
                                    </select>
                                </div>

                                {/* Error Message */}
                                {error && (
                                    <div className="flex items-center gap-2 p-3 bg-red-950/50 border border-red-500/30 rounded-lg">
                                        <AlertCircle className="w-5 h-5 text-red-400" />
                                        <p className="text-sm text-red-300">{error}</p>
                                    </div>
                                )}
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
                                    onClick={handleSubmit}
                                    disabled={loading}
                                    className="px-4 py-2 bg-red-600 hover:bg-red-700 text-white rounded-lg transition-colors disabled:opacity-50 flex items-center gap-2"
                                >
                                    {loading ? (
                                        <>
                                            <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                                            Blocking...
                                        </>
                                    ) : (
                                        <>
                                            <Shield className="w-4 h-4" />
                                            Block IP
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
