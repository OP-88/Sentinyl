import { useState, useEffect } from 'react';
import { io } from 'socket.io-client';
import { motion, AnimatePresence } from 'framer-motion';
import {
    Wifi,
    WifiOff,
    Shield,
    Key,
    AlertTriangle,
    Activity,
    Skull
} from 'lucide-react';
import TerminalLog from '../components/TerminalLog';
import StatusCard from '../components/StatusCard';

const SOCKET_URL = 'http://localhost:3000';
const MAX_LOGS = 100;

/**
 * Overwatch Page - Real-time security event monitoring
 * 
 * Dedicated page for Ghost Protocol and Lazarus event stream
 */
export default function Overwatch() {
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
    }, []);

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

    return (
        <div className="min-h-full bg-gradient-to-br from-slate-950 via-blue-950 to-slate-950 text-gray-100">
            {/* SUICIDE ALERT OVERLAY */}
            <AnimatePresence>
                {showSuicideAlert && (
                    <motion.div
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        exit={{ opacity: 0 }}
                        className="fixed inset-0 z-50 flex items-center justify-center bg-red-950/95 backdrop-blur-sm"
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

            {/* MAIN CONTENT */}
            <div className="p-6">
                {/* Header */}
                <motion.div
                    initial={{ y: -20, opacity: 0 }}
                    animate={{ y: 0, opacity: 1 }}
                    className="mb-6"
                >
                    <div className="flex items-center gap-3 mb-2">
                        <Shield className="w-8 h-8 text-cyan-400" />
                        <h1 className="text-3xl font-bold text-cyan-400">OVERWATCH</h1>
                    </div>
                    <p className="text-slate-400">Real-time Security Event Stream</p>
                    <div className="mt-2 h-1 bg-gradient-to-r from-cyan-500 via-blue-500 to-purple-500 rounded-full"></div>
                </motion.div>

                <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
                    {/* Stats Sidebar */}
                    <div className="lg:col-span-1 space-y-4">
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
                            <div className="text-xs text-slate-500 mt-4">
                                Last event: {new Date(systemStatus.lastEvent).toLocaleTimeString()}
                            </div>
                        )}
                    </div>

                    {/* Terminal Log */}
                    <div className="lg:col-span-3">
                        <motion.div
                            initial={{ opacity: 0, y: 20 }}
                            animate={{ opacity: 1, y: 0 }}
                            className="h-[calc(100vh-200px)]"
                        >
                            <TerminalLog logs={logs} />
                        </motion.div>
                    </div>
                </div>
            </div>
        </div>
    );
}
