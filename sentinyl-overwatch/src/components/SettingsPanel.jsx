import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { X, Key, Shield, Copy, Check, Eye, EyeOff } from 'lucide-react';
import { useUser } from '../context/UserContext';

/**
 * Settings Panel - API Key and Tier Management
 * 
 * Provides interface for:
 * - Viewing/copying API key
 * - Updating API key
 * - Viewing current tier
 * - Changing tier (for testing)
 */
export default function SettingsPanel({ isOpen, onClose }) {
    const { apiKey, tier, login, updateTier } = useUser();
    const [showApiKey, setShowApiKey] = useState(false);
    const [copied, setCopied] = useState(false);
    const [newApiKey, setNewApiKey] = useState('');
    const [selectedTier, setSelectedTier] = useState(tier);

    const handleCopyApiKey = () => {
        if (apiKey) {
            navigator.clipboard.writeText(apiKey);
            setCopied(true);
            setTimeout(() => setCopied(false), 2000);
        }
    };

    const handleUpdateApiKey = () => {
        if (newApiKey.trim()) {
            login(newApiKey.trim(), tier);
            setNewApiKey('');
            alert('API Key updated successfully!');
        }
    };

    const handleUpdateTier = () => {
        if (selectedTier !== tier) {
            updateTier(selectedTier);
            alert(`Tier updated to: ${selectedTier}`);
        }
    };

    const tiers = [
        { value: 'free', label: 'Free', description: 'Limited features' },
        { value: 'scout_pro', label: 'Scout Pro', description: 'Advanced threat scanning' },
        { value: 'guard_lite', label: 'Guard Lite', description: 'Active defense monitoring' },
        { value: 'full_stack', label: 'Full Stack', description: 'All features unlocked' }
    ];

    const maskApiKey = (key) => {
        if (!key) return 'Not configured';
        if (key.length <= 12) return '••••••••';
        return `${key.substring(0, 8)}${'•'.repeat(key.length - 12)}${key.substring(key.length - 4)}`;
    };

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
                        className="fixed inset-0 bg-black/60 backdrop-blur-sm z-40"
                    />

                    {/* Panel */}
                    <motion.div
                        initial={{ x: '100%' }}
                        animate={{ x: 0 }}
                        exit={{ x: '100%' }}
                        transition={{ type: 'spring', damping: 25, stiffness: 200 }}
                        className="fixed right-0 top-0 h-full w-full max-w-md bg-slate-900 shadow-2xl z-50 overflow-y-auto"
                    >
                        <div className="p-6">
                            {/* Header */}
                            <div className="flex items-center justify-between mb-6">
                                <div className="flex items-center gap-3">
                                    <div className="p-2 bg-cyan-500/20 rounded-lg">
                                        <Shield className="w-6 h-6 text-cyan-400" />
                                    </div>
                                    <h2 className="text-2xl font-bold text-white">Settings</h2>
                                </div>
                                <button
                                    onClick={onClose}
                                    className="p-2 hover:bg-slate-800 rounded-lg transition-colors"
                                >
                                    <X className="w-5 h-5 text-slate-400" />
                                </button>
                            </div>

                            {/* API Key Section */}
                            <div className="mb-8">
                                <div className="flex items-center gap-2 mb-4">
                                    <Key className="w-5 h-5 text-cyan-400" />
                                    <h3 className="text-lg font-semibold text-white">API Key</h3>
                                </div>

                                {/* Current API Key Display */}
                                <div className="bg-slate-800/50 border border-slate-700 rounded-lg p-4 mb-4">
                                    <label className="text-xs text-slate-400 mb-2 block">Current API Key</label>
                                    <div className="flex items-center gap-2">
                                        <code className="flex-1 text-sm font-mono text-white bg-slate-950 px-3 py-2 rounded border border-slate-700">
                                            {showApiKey ? (apiKey || 'Not configured') : maskApiKey(apiKey)}
                                        </code>
                                        <button
                                            onClick={() => setShowApiKey(!showApiKey)}
                                            className="p-2 hover:bg-slate-700 rounded transition-colors"
                                            title={showApiKey ? 'Hide' : 'Show'}
                                        >
                                            {showApiKey ? (
                                                <EyeOff className="w-4 h-4 text-slate-400" />
                                            ) : (
                                                <Eye className="w-4 h-4 text-slate-400" />
                                            )}
                                        </button>
                                        <button
                                            onClick={handleCopyApiKey}
                                            disabled={!apiKey}
                                            className="p-2 hover:bg-slate-700 rounded transition-colors disabled:opacity-50"
                                            title="Copy to clipboard"
                                        >
                                            {copied ? (
                                                <Check className="w-4 h-4 text-green-400" />
                                            ) : (
                                                <Copy className="w-4 h-4 text-slate-400" />
                                            )}
                                        </button>
                                    </div>
                                </div>

                                {/* Update API Key */}
                                <div className="bg-slate-800/50 border border-slate-700 rounded-lg p-4">
                                    <label className="text-xs text-slate-400 mb-2 block">Update API Key</label>
                                    <input
                                        type="password"
                                        value={newApiKey}
                                        onChange={(e) => setNewApiKey(e.target.value)}
                                        placeholder="Paste new API key..."
                                        className="w-full bg-slate-950 border border-slate-700 rounded px-3 py-2 text-white text-sm mb-3 focus:outline-none focus:border-cyan-500"
                                    />
                                    <button
                                        onClick={handleUpdateApiKey}
                                        disabled={!newApiKey.trim()}
                                        className="w-full bg-cyan-600 hover:bg-cyan-700 disabled:bg-slate-700 disabled:text-slate-500 text-white font-medium py-2 px-4 rounded transition-colors"
                                    >
                                        Update API Key
                                    </button>
                                </div>
                            </div>

                            {/* Subscription Tier Section */}
                            <div className="mb-8">
                                <div className="flex items-center gap-2 mb-4">
                                    <Shield className="w-5 h-5 text-purple-400" />
                                    <h3 className="text-lg font-semibold text-white">Subscription Tier</h3>
                                </div>

                                {/* Current Tier Display */}
                                <div className="bg-slate-800/50 border border-slate-700 rounded-lg p-4 mb-4">
                                    <label className="text-xs text-slate-400 mb-2 block">Current Tier</label>
                                    <div className="flex items-center gap-3">
                                        <div className="flex-1">
                                            <div className="text-lg font-bold text-white capitalize">
                                                {tier.replace('_', ' ')}
                                            </div>
                                            <div className="text-xs text-slate-400">
                                                {tiers.find(t => t.value === tier)?.description}
                                            </div>
                                        </div>
                                    </div>
                                </div>

                                {/* Change Tier (for testing) */}
                                <div className="bg-slate-800/50 border border-slate-700 rounded-lg p-4">
                                    <label className="text-xs text-slate-400 mb-2 block">
                                        Change Tier
                                        <span className="ml-2 text-yellow-400">(Testing Only)</span>
                                    </label>
                                    <select
                                        value={selectedTier}
                                        onChange={(e) => setSelectedTier(e.target.value)}
                                        className="w-full bg-slate-950 border border-slate-700 rounded px-3 py-2 text-white text-sm mb-3 focus:outline-none focus:border-cyan-500"
                                    >
                                        {tiers.map(t => (
                                            <option key={t.value} value={t.value}>
                                                {t.label} - {t.description}
                                            </option>
                                        ))}
                                    </select>
                                    <button
                                        onClick={handleUpdateTier}
                                        disabled={selectedTier === tier}
                                        className="w-full bg-purple-600 hover:bg-purple-700 disabled:bg-slate-700 disabled:text-slate-500 text-white font-medium py-2 px-4 rounded transition-colors"
                                    >
                                        Update Tier
                                    </button>
                                    <p className="text-xs text-slate-500 mt-2">
                                        Note: In production, tier changes would require billing updates via Stripe.
                                    </p>
                                </div>
                            </div>

                            {/* About Section */}
                            <div className="border-t border-slate-700 pt-6">
                                <div className="text-center text-sm text-slate-400">
                                    <p className="mb-1">Sentinyl Overwatch Dashboard</p>
                                    <p className="text-xs text-slate-500">v1.0.0</p>
                                </div>
                            </div>
                        </div>
                    </motion.div>
                </>
            )}
        </AnimatePresence>
    );
}
