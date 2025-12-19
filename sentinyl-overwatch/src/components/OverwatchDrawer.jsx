import { useState, useEffect } from 'react';
import { createPortal } from 'react-dom';
import { motion, AnimatePresence } from 'framer-motion';
import { X, Wifi, WifiOff, Shield, Key, AlertTriangle, Activity, Skull } from 'lucide-react';
import { io } from 'socket.io-client';
import TerminalLog from './TerminalLog';
import StatusCard from './StatusCard';

const SOCKET_URL = 'http://localhost:3000';
const MAX_LOGS = 100;

/**
 * OverwatchDrawer - Slide-in overlay for real-time event monitoring
 * 
 * Opens as a drawer from the right side with backdrop blur
 * Maintains original cyberpunk UI aesthetic
 */
export default function OverwatchDrawer({ isOpen, onClose }) {
    const [socket, setSocket] = useState(null);
    const [logs, setLogs] = useState([]);
    const [systemStatus, setSystemStatus] = useState({
        bridge: 'OFFLINE',
        totalKnocks: 0,
        acceptedKnocks: 0,
        rejectedKnocks: 0,
        recoveryAttempts: 0,
        suicideTriggered: false,
        lastEvent: null
    });
    const [showSuicideAlert, setShowSuicideAlert] = useState(false);

    // Socket.io connection
    useEffect(() => {
        if (!isOpen) return;

        const newSocket = io(SOCKET_URL, {
            transports: ['websocket'],
            reconnection: true,
            reconnectionDelay: 1000,
            reconnectionAttempts: 10
        });

        newSocket.on('connect', () => {
            console.log('🟢 Connected to Sentinyl Bridge');
            setSystemStatus(prev => ({
                ...prev,
                bridge: 'ONLINE'
            }));
            addLog({
                type: 'HEARTBEAT',
                status: 'ONLINE',
                timestamp: Date.now()
            });
        });

        newSocket.on('disconnect', () => {
            console.log('🔴 Disconnected from Sentinyl Bridge');
            setSystemStatus(prev => ({
                ...prev,
                bridge: 'OFFLINE'
            }));
            addLog({
                type: 'HEARTBEAT',
                status: 'OFFLINE',
                timestamp: Date.now()
            });
        });

        newSocket.on('dashboard_event', (event) => {
            console.log('📡 Event received:', event);
            handleDashboardEvent(event);
        });

        setSocket(newSocket);

        return () => {
            newSocket.close();
        };
    }, [isOpen]);

    const addLog = (event) => {
        const logEntry = {
            ...event,
            timestamp: event.timestamp || Date.now()
        };

        setLogs(prev => {
            const updated = [logEntry, ...prev].slice(0, MAX_LOGS);
            return updated;
        });
    };

    const handleDashboardEvent = (event) => {
        addLog(event);

        setSystemStatus(prev => {
            const updated = { ...prev, lastEvent: Date.now() };

            switch (event.type?.toUpperCase()) {
                case 'KNOCK':
                    updated.totalKnocks = prev.totalKnocks + 1;
                    if (event.status === 'ACCEPTED') {
                        updated.acceptedKnocks = prev.acceptedKnocks + 1;
                    } else {
                        updated.rejectedKnocks = prev.rejectedKnocks + 1;
                    }
                    break;

                case 'RECOVERY':
                    updated.recoveryAttempts = prev.recoveryAttempts + 1;
                    break;

                case 'SUICIDE':
                    updated.suicideTriggered = true;
                    setShowSuicideAlert(true);
                    setTimeout(() => setShowSuicideAlert(false), 5000);
                    break;

                default:
                    break;
            }

            return updated;
        });
    };

    if (!isOpen) return null;

    return createPortal(
        <AnimatePresence>
            {isOpen && (
                <>
                    {/* Backdrop with blur */}
                    <motion.div
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        exit={{ opacity: 0 }}
                        onClick={onClose}
                        className="fixed inset-0 bg-black/50 backdrop-blur-sm z-40"
                    />

                    {/* Drawer */}
                    <motion.div
                        initial={{ x: '100%' }}
                        animate={{ x: 0 }}
                        exit={{ x: '100%' }}
                        transition={{ type: 'spring', damping: 30, stiffness: 300 }}
                        className="fixed right-0 top-0 h-full w-full lg:w-4/5 xl:w-3/4 bg-gray-950 z-50 shadow-2xl overflow-hidden"
                    >
                        {/* SUICIDE ALERT OVERLAY */}
                        <AnimatePresence>
                            {showSuicideAlert && (
                                <motion.div
                                    initial={{ opacity: 0 }}
                                    animate={{ opacity: 1 }}
                                    exit={{ opacity: 0 }}
                                    className="absolute inset-0 z-50 flex items-center justify-center bg-red-950/95 backdrop-blur-sm"
                                >
                                    <motion.div
                                        animate={{
                                            scale: [1, 1.05, 1],
                                            rotate: [0, 1, -1, 0]
                                        }}
                                        transition={{
                                            repeat: Infinity,
                                            duration: 0.5
                                        }}
                                        className="text-center"
                                    >
                                        <Skull className="w-32 h-32 text-red-500 mx-auto mb-6" />
                                        <motion.h1
                                            animate={{
                                                opacity: [1, 0.5, 1],
                                                textShadow: [
                                                    '0 0 20px #ff0000',
                                                    '0 0 40px #ff0000',
                                                    '0 0 20px #ff0000'
                                                ]
                                            }}
                                            transition={{
                                                repeat: Infinity,
                                                duration: 0.8
                                            }}
                                            className="text-6xl font-bold text-red-500 mb-4 font-mono"
                                        >
                                            ⚠ SUICIDE PROTOCOL TRIGGERED ⚠
                                        </motion.h1>
                                        <p className="text-2xl text-red-300 font-mono">
                                            LAZARUS RECOVERY SYSTEM TERMINATED
                                        </p>
                                        <p className="text-red-400 mt-4 font-mono text-sm">
                                            Maximum failed attempts exceeded. Service shutdown initiated.
                                        </p>
                                    </motion.div>
                                </motion.div>
                            )}
                        </AnimatePresence>

                        {/* Header */}
                        <div className="bg-gray-900 border-b border-green-500/30 p-6 flex items-center justify-between">
                            <motion.div
                                initial={{ y: -20, opacity: 0 }}
                                animate={{ y: 0, opacity: 1 }}
                            >
                                <div className="flex items-center gap-3 mb-2">
                                    <Shield className="w-8 h-8 text-green-400" />
                                    <h1 className="text-2xl font-bold font-mono text-green-400">SENTINYL OVERWATCH</h1>
                                </div>
                                <p className="text-gray-500 text-sm font-mono">Real-time Security Event Stream</p>
                                <div className="mt-2 h-1 bg-gradient-to-r from-green-500 via-cyan-500 to-blue-500 rounded-full"></div>
                            </motion.div>

                            {/* Close Button */}
                            <button
                                onClick={onClose}
                                className="p-2 hover:bg-gray-800 rounded-lg transition-colors"
                            >
                                <X className="w-6 h-6 text-gray-400 hover:text-white" />
                            </button>
                        </div>

                        {/* Content */}
                        <div className="h-[calc(100%-120px)] overflow-y-auto">
                            <div className="flex h-full">
                                {/* Stats Sidebar */}
                                <div className="w-80 bg-gray-900 border-r border-green-500/30 p-6 overflow-y-auto">
                                    <div className="space-y-4">
                                        <StatusCard
                                            title="Bridge Status"
                                            value={systemStatus.bridge}
                                            icon={systemStatus.bridge === 'ONLINE' ? Wifi : WifiOff}
                                            status={systemStatus.bridge}
                                            pulse={true}
                                            description="Socket.io Connection"
                                        />

                                        <StatusCard
                                            title="Ghost Knocks"
                                            value={systemStatus.totalKnocks}
                                            icon={Shield}
                                            status={systemStatus.bridge}
                                            description={`${systemStatus.acceptedKnocks} accepted / ${systemStatus.rejectedKnocks} rejected`}
                                        />

                                        <StatusCard
                                            title="Recovery Attempts"
                                            value={systemStatus.recoveryAttempts}
                                            icon={Key}
                                            status={systemStatus.bridge}
                                            description="Lazarus activations"
                                        />

                                        <StatusCard
                                            title="System Health"
                                            value={systemStatus.suicideTriggered ? 'CRITICAL' : 'NOMINAL'}
                                            icon={systemStatus.suicideTriggered ? AlertTriangle : Activity}
                                            status={systemStatus.suicideTriggered ? 'CRITICAL' : 'ONLINE'}
                                            pulse={true}
                                            description={systemStatus.suicideTriggered ? 'Suicide switch activated' : 'All systems operational'}
                                        />

                                        {systemStatus.lastEvent && (
                                            <div className="text-xs text-gray-600 font-mono mt-4">
                                                Last event: {new Date(systemStatus.lastEvent).toLocaleTimeString()}
                                            </div>
                                        )}
                                    </div>
                                </div>

                                {/* Terminal Log */}
                                <div className="flex-1 p-6">
                                    <motion.div
                                        initial={{ opacity: 0, y: 20 }}
                                        animate={{ opacity: 1, y: 0 }}
                                        className="h-full"
                                    >
                                        <TerminalLog logs={logs} />
                                    </motion.div>
                                </div>
                            </div>
                        </div>
                    </motion.div>
                </>
            )}
        </AnimatePresence>,
        document.body
    );
}
