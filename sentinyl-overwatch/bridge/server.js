import express from 'express';
import { createServer } from 'http';
import { Server } from 'socket.io';
import cors from 'cors';

const app = express();
const httpServer = createServer(app);

// Configure CORS für Express
app.use(cors({
    origin: 'http://localhost:5173',
    credentials: true
}));

app.use(express.json());

// Socket.IO configuration
const io = new Server(httpServer, {
    cors: {
        origin: 'http://localhost:5173',
        methods: ['GET', 'POST'],
        credentials: true
    },
    transports: ['websocket', 'polling']
});

const PORT = process.env.PORT || 3000;

// Connection tracking
let connectedClients = 0;

// Socket.IO event handlers
io.on('connection', (socket) => {
    connectedClients++;
    console.log(`✅ Dashboard client connected [ID: ${socket.id}] - Total clients: ${connectedClients}`);

    // Send welcome message
    socket.emit('dashboard_event', {
        type: 'HEARTBEAT',
        status: 'ONLINE',
        timestamp: Date.now()
    });

    socket.on('disconnect', () => {
        connectedClients--;
        console.log(`❌ Dashboard client disconnected [ID: ${socket.id}] - Total clients: ${connectedClients}`);
    });
});

// REST API for backend to push events
app.post('/api/events/knock', (req, res) => {
    const { ip, status, timestamp } = req.body;

    const event = {
        type: 'KNOCK',
        ip: ip || 'unknown',
        status: status || 'UNKNOWN',
        timestamp: timestamp || Date.now()
    };

    console.log(`📡 Broadcasting KNOCK event:`, event);
    io.emit('dashboard_event', event);

    res.json({ success: true, event });
});

app.post('/api/events/recovery', (req, res) => {
    const { ip, status, timestamp, details } = req.body;

    const event = {
        type: 'RECOVERY',
        ip: ip || 'unknown',
        status: status || 'UNKNOWN',
        timestamp: timestamp || Date.now(),
        details: details || {}
    };

    console.log(`📡 Broadcasting RECOVERY event:`, event);
    io.emit('dashboard_event', event);

    res.json({ success: true, event });
});

app.post('/api/events/suicide', (req, res) => {
    const { timestamp, reason } = req.body;

    const event = {
        type: 'SUICIDE',
        status: 'TRIGGERED',
        timestamp: timestamp || Date.now(),
        reason: reason || 'Maximum failed attempts exceeded'
    };

    console.log(`🚨 Broadcasting SUICIDE event:`, event);
    io.emit('dashboard_event', event);

    res.json({ success: true, event });
});

app.post('/api/events/custom', (req, res) => {
    const event = {
        ...req.body,
        timestamp: req.body.timestamp || Date.now()
    };

    console.log(`📡 Broadcasting CUSTOM event:`, event);
    io.emit('dashboard_event', event);

    res.json({ success: true, event });
});

// Health check
app.get('/health', (req, res) => {
    res.json({
        status: 'healthy',
        service: 'sentinyl-overwatch-bridge',
        connectedClients,
        uptime: process.uptime()
    });
});

// Start server
httpServer.listen(PORT, () => {
    console.log(`
╔════════════════════════════════════════════════════════════╗
║                                                            ║
║         🛡️  SENTINYL OVERWATCH BRIDGE SERVER 🛡️          ║
║                                                            ║
║  Socket.IO Bridge: http://localhost:${PORT}                    ║
║  Dashboard UI:     http://localhost:5173                   ║
║                                                            ║
║  REST API Endpoints:                                       ║
║    POST /api/events/knock      - Ghost Protocol events    ║
║    POST /api/events/recovery   - Lazarus events           ║
║    POST /api/events/suicide    - Suicide switch events    ║
║    POST /api/events/custom     - Custom events            ║
║    GET  /health                - Health check             ║
║                                                            ║
╚════════════════════════════════════════════════════════════╝
    `);
});

// Graceful shutdown
process.on('SIGTERM', () => {
    console.log('🛑 SIGTERM received, shutting down gracefully...');
    httpServer.close(() => {
        console.log('✅ Server closed');
        process.exit(0);
    });
});

process.on('SIGINT', () => {
    console.log('\n🛑 SIGINT received, shutting down gracefully...');
    httpServer.close(() => {
        console.log('✅ Server closed');
        process.exit(0);
    });
});
