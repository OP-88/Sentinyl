import { motion, AnimatePresence } from 'framer-motion';
import { Terminal, Shield, AlertTriangle, Activity } from 'lucide-react';

/**
 * TerminalLog - Cyberpunk-styled scrolling event log
 * 
 * Displays real-time security events with color-coded severity
 * and smooth animations for that authentic SOC feel.
 */
export default function TerminalLog({ logs = [] }) {
    const getLogStyle = (log) => {
        const baseClasses = "font-mono text-sm py-2 px-4 border-l-2 ";

        switch (log.status?.toUpperCase()) {
            case 'ACCEPTED':
            case 'SUCCESS':
            case 'ONLINE':
                return baseClasses + "border-green-500 text-green-400 bg-green-950/20";

            case 'REJECTED':
            case 'FAILED':
            case 'OFFLINE':
                return baseClasses + "border-red-500 text-red-400 bg-red-950/20";

            case 'TRIGGERED':
                return baseClasses + "border-red-600 text-red-300 bg-red-950/40 animate-pulse";

            default:
                return baseClasses + "border-blue-500 text-blue-400 bg-blue-950/20";
        }
    };

    const getIcon = (type) => {
        switch (type?.toUpperCase()) {
            case 'KNOCK':
                return <Shield className="w-4 h-4" />;
            case 'RECOVERY':
                return <Activity className="w-4 h-4" />;
            case 'SUICIDE':
                return <AlertTriangle className="w-4 h-4" />;
            default:
                return <Terminal className="w-4 h-4" />;
        }
    };

    const formatTimestamp = (timestamp) => {
        const date = new Date(timestamp);
        return date.toLocaleTimeString('en-US', {
            hour12: false,
            hour: '2-digit',
            minute: '2-digit',
            second: '2-digit'
        });
    };

    return (
        <div className="bg-black rounded-lg border border-green-500/30 shadow-lg shadow-green-500/10 h-full overflow-hidden">
            {/* Header */}
            <div className="bg-gray-900 border-b border-green-500/30 px-4 py-3 flex items-center gap-3">
                <Terminal className="w-5 h-5 text-green-400" />
                <h2 className="text-green-400 font-mono font-bold tracking-wider">LIVE EVENT STREAM</h2>
                <div className="ml-auto flex items-center gap-2">
                    <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse"></div>
                    <span className="text-green-500 text-xs font-mono">MONITORING</span>
                </div>
            </div>

            {/* Log Container */}
            <div className="h-[calc(100%-60px)] overflow-y-auto scrollbar-thin scrollbar-thumb-green-500/50 scrollbar-track-gray-900">
                <div className="p-2 space-y-1">
                    <AnimatePresence initial={false}>
                        {logs.length === 0 ? (
                            <motion.div
                                initial={{ opacity: 0 }}
                                animate={{ opacity: 1 }}
                                className="text-gray-600 font-mono text-sm p-4 text-center"
                            >
                                → Awaiting security events...
                            </motion.div>
                        ) : (
                            logs.slice().reverse().map((log, index) => (
                                <motion.div
                                    key={`${log.timestamp}-${index}`}
                                    initial={{ opacity: 0, x: -20, scale: 0.95 }}
                                    animate={{ opacity: 1, x: 0, scale: 1 }}
                                    exit={{ opacity: 0, scale: 0.95 }}
                                    transition={{ duration: 0.3, ease: "easeOut" }}
                                    className={getLogStyle(log)}
                                >
                                    <div className="flex items-center gap-3">
                                        {/* Timestamp */}
                                        <span className="text-gray-500 text-xs font-mono min-w-[80px]">
                                            {formatTimestamp(log.timestamp)}
                                        </span>

                                        {/* Icon */}
                                        <div className="flex-shrink-0">
                                            {getIcon(log.type)}
                                        </div>

                                        {/* Event Type */}
                                        <span className="font-bold min-w-[100px]">
                                            [{log.type}]
                                        </span>

                                        {/* Details */}
                                        <span className="flex-1">
                                            {log.ip && <span className="text-cyan-400">{log.ip}</span>}
                                            {log.status && (
                                                <span className={`ml-2 ${log.status.toUpperCase() === 'ACCEPTED' || log.status.toUpperCase() === 'SUCCESS'
                                                        ? 'text-green-300'
                                                        : log.status.toUpperCase() === 'TRIGGERED'
                                                            ? 'text-red-300 font-bold'
                                                            : 'text-red-400'
                                                    }`}>
                                                    {log.status.toUpperCase()}
                                                </span>
                                            )}
                                        </span>

                                        {/* Glitch effect for SUICIDE events */}
                                        {log.type === 'SUICIDE' && (
                                            <motion.span
                                                animate={{
                                                    opacity: [1, 0.3, 1],
                                                    textShadow: [
                                                        '0 0 10px #ff0000',
                                                        '0 0 20px #ff0000',
                                                        '0 0 10px #ff0000'
                                                    ]
                                                }}
                                                transition={{
                                                    repeat: Infinity,
                                                    duration: 0.5
                                                }}
                                                className="text-red-500 font-bold text-xs"
                                            >
                                                ⚠ CRITICAL ⚠
                                            </motion.span>
                                        )}
                                    </div>
                                </motion.div>
                            ))
                        )}
                    </AnimatePresence>
                </div>
            </div>
        </div>
    );
}
