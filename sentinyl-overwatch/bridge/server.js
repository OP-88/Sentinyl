import express from 'express';
import { createServer } from 'http';
import { Server } from 'socket.io';
import cors from 'cors';
import axios from 'axios';
import dotenv from 'dotenv';
import { RateLimiterMemory } from 'rate-limiter-flexible';

// Load environment variables
dotenv.config();

const app = express();
const httpServer = createServer(app);

// Environment configuration
const PORT = process.env.PORT || 3000;
const BACKEND_API_URL = process.env.BACKEND_API_URL || 'http://localhost:8000';
const ALLOWED_ORIGINS = (process.env.ALLOWED_ORIGINS || 'http://localhost:5173').split(',').map(o => o.trim());

// Rate limiter - 100 events per minute per connection
const rateLimiter = new RateLimiterMemory({
    points: parseInt(process.env.RATE_LIMIT_POINTS || '100'),
    duration: parseInt(process.env.RATE_LIMIT_DURATION || '60')
});

// Configure CORS for Express
app.use(cors({
    origin: ALLOWED_ORIGINS,
    credentials: true
}));

app.use(express.json());

// Socket.IO configuration with authentication
const io = new Server(httpServer, {
    cors: {
        origin: ALLOWED_ORIGINS,
        methods: ['GET', 'POST'],
        credentials: true
    },
    transports: ['websocket', 'polling']
});

// Connection tracking
let connectedClients = 0;
const authenticatedClients = new Map(); // Map of socket.id -> user info

/**
 * Validate API key with backend
 */
async function validateApiKey(apiKey) {
    if (!apiKey) {
        return { valid: false, error: 'No API key provided' };
    }

    try {
        const response = await axios.get(`${BACKEND_API_URL}/auth/me`, {
            headers: {
                'Authorization': `Bearer ${apiKey}`
            },
            timeout: 5000
        });

        return {
            valid: true,
            user: response.data
        };
    } catch (error) {
        if (error.response) {
            return {
                valid: false,
                error: `Authentication failed: ${error.response.status}`
            };
        }
        return {
            valid: false,
            error: 'Unable to validate API key - backend unreachable'
        };
    }
}

// Authentication middleware for Socket.IO
io.use(async (socket, next) => {
    const apiKey = socket.handshake.auth?.apiKey;

    if (!apiKey) {
        return next(new Error('Authentication required - No API key provided'));
    }

    const validation = await validateApiKey(apiKey);

    if (!validation.valid) {
        return next(new Error(validation.error));
    }

    // Store user info in socket data
    socket.data.user = validation.user;
    next();
});

// Socket.IO event handlers
io.on('connection', (socket) => {
    connectedClients++;
    const user = socket.data.user;

    authenticatedClients.set(socket.id, {
        userId: user.user_id || user.email,
        tier: user.tier,
        connectedAt: new Date()
    });

    console.log(`✅ Authenticated client connected [ID: ${socket.id}] - User: ${user.email || 'unknown'} (${user.tier}) - Total: ${connectedClients}`);

    // Send welcome message
    socket.emit('dashboard_event', {
        type: 'HEARTBEAT',
        status: 'ONLINE',
        timestamp: Date.now(),
        user: {
            tier: user.tier
        }
    });

    // Connection timeout (30 seconds idle)
    let idleTimeout = setTimeout(() => {
        console.log(`⏱️  Client ${socket.id} idle timeout - disconnecting`);
        socket.disconnect(true);
    }, 30000);

    // Reset timeout on any activity
    socket.onAny(() => {
        clearTimeout(idleTimeout);
        idleTimeout = setTimeout(() => {
            console.log(`⏱️  Client ${socket.id} idle timeout - disconnecting`);
            socket.disconnect(true);
        }, 30000);
    });

    socket.on('disconnect', () => {
        connectedClients--;
        clearTimeout(idleTimeout);
        authenticatedClients.delete(socket.id);
        console.log(`❌ Client disconnected [ID: ${socket.id}] - Total: ${connectedClients}`);
    });

    socket.on('error', (error) => {
        console.error(`Socket error [${socket.id}]:`, error);
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
