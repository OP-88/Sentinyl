# Sentinyl Overwatch 🛡️

**Real-time Security Operations Center Dashboard**

Cyberpunk-styled React dashboard for monitoring Sentinyl security events in real-time.

## Features

- 🔴 **Live Event Stream**: Real-time security event monitoring via Socket.io
- 📊 **System Stats**: Bridge status, Ghost Protocol knocks, Lazarus recovery attempts
- 🚨 **Red Alert**: Fullscreen suicide protocol warnings
- 🎨 **Cyberpunk Aesthetic**: Dark mode, neon accents, terminal fonts
- ⚡ **Smooth Animations**: Framer Motion powered transitions and effects

## Quick Start

```bash
# Install dependencies
npm install

# Start development server
npm run dev

# Build for production
npm run build
```

## Architecture

```
Sentinyl Backend → Redis Pub/Sub → Node.js Bridge (port 3000)
                                         ↓
                                  Socket.io Server
                                         ↓
                              React Dashboard (port 5173)
```

## Event Types

The dashboard listens for these event types:

- `KNOCK` - Ghost Protocol authentication attempts
- `RECOVERY` - Lazarus recovery system activations
- `SUICIDE` - Lazarus suicide switch triggers (shows fullscreen alert)
- `HEARTBEAT` - System health checks

## Tech Stack

- **React 18** - UI framework
- **Vite** - Build tool
- **Tailwind CSS** - Utility-first styling
- **Socket.io Client** - Real-time communication
- **Framer Motion** - Animations
- **Lucide React** - Icons

## Customization

### Colors

Edit `tailwind.config.js` to customize the cyberpunk color palette:

```js
colors: {
  'cyber-green': '#00ff41',
  'cyber-blue': '#00d4ff',
  'cyber-pink': '#ff006e',
}
```

### Connections

Update Socket.io URL in `src/App.jsx`:

```js
const SOCKET_URL = 'http://localhost:3000';
```

## Screenshots

*(Coming soon - dashboard in action)*

---

**Built for OP-88's Sentinyl Security Platform**
