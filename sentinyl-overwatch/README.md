# Sentinyl Overwatch 🛡️

**Enterprise Security Operations Center Dashboard**

Modern, cyberpunk-styled React dashboard for real-time security monitoring and threat response across all Sentinyl modules.

## ✨ Features

### 🎨 UI/UX
- **Header-Only Layout** - Maximized screen real estate with full-width content
- **Ambient Lighting Effects** - Color-coded glows on all interactive elements (zero blur/shake)
- **Tier-Based Visibility** - Features automatically show/hide based on subscription
- **Settings Panel** - API key management and tier switching
- **No Scale Animations** - Crisp, professional interactions without visual artifacts

### 🔴 Real-Time Monitoring
- **Live Event Stream** - Socket.IO powered real-time security events
- **Overwatch Drawer** - Slide-in panel for Ghost Protocol & Lazarus monitoring
- **System Status** - Bridge status, knock attempts, recovery activations
- **Suicide Protocol Alerts** - Fullscreen red alert warnings

### ⚡ Quick Actions
- **Typosquat Scan** - Domain variation scanning (Scout Pro tier)
- **GitHub Leak Scan** - Credential exposure detection (Scout Pro tier)
- **Block IP** - IP blocklist management with validation (Guard Lite tier)
- **Export Data** - Multi-format report export (JSON/CSV/PDF)
- **View Overwatch** - Real-time event monitoring (Guard Lite tier)

### 📊 Dashboard Components
- **Status Cards** - Threat metrics with ambient hover effects
- **Threat Charts** - Visual analytics for security trends
- **Alerts Table** - Recent security incidents
- **Terminal Log** - Scrolling event feed with color coding

## 🚀 Quick Start

```bash
# Install dependencies
npm install

# Start development server
npm run dev

# Build for production
npm run build
```

## 🏗️ Architecture

```
┌─────────────────┐         ┌──────────────┐         ┌─────────────────┐
│  FastAPI Backend│────────▶│ Redis Pub/Sub│◀────────│  Node.js Bridge │
│  (port 8000)    │         │              │         │   (port 3000)   │
└─────────────────┘         └──────────────┘         └─────────────────┘
                                                               │
                                                               │ Socket.IO
                                                               ▼
                                                      ┌─────────────────┐
                                                      │ React Dashboard │
                                                      │   (port 5173)   │
                                                      └─────────────────┘
```

## 📡 Event Types

| Type | Description | UI Response |
|------|-------------|-------------|
| `KNOCK` | Ghost Protocol auth attempts | Green/Red log entry |
| `RECOVERY` | Lazarus activation | Increments counter |
| `SUICIDE` | Suicide switch triggered | Fullscreen red alert |
| `HEARTBEAT` | System health check | Status indicator |

## 🎯 Subscription Tiers

### Free Tier
- Basic dashboard access
- Limited features

### Scout Pro ($29/month)
- ✅ Typosquat scanning
- ✅ GitHub leak detection
- ✅ Threat analytics

### Guard Lite ($49/month)
- ✅ IP blocking
- ✅ Overwatch monitoring
- ✅ Real-time alerts

### Full Stack ($99/month)
- ✅ All Scout Pro features
- ✅ All Guard Lite features
- ✅ Ghost Protocol integration
- ✅ Lazarus Recovery system

## 🛠️ Tech Stack

| Category | Technology |
|----------|-----------|
| Framework | React 18 |
| Build Tool | Vite |
| Styling | Tailwind CSS |
| Real-time | Socket.IO Client |
| Animations | Framer Motion |
| Icons | Lucide React |
| Routing | React Router DOM |

## ⚙️ Configuration

### Environment Variables

Create `.env` file:

```bash
VITE_API_BASE_URL=http://localhost:8000
VITE_SOCKET_URL=http://localhost:3000
```

### Socket.IO Connection

Update in `src/components/OverwatchDrawer.jsx`:

```javascript
const SOCKET_URL = 'http://localhost:3000';
```

## 🔒 Security Features

- **API Key Authentication** - Secure backend communication
- **IP Validation** - Regex-based IPv4 validation for blocklist
- **Tier-Based Access Control** - Feature gating based on subscription
- **CORS Protection** - Backend origin restrictions (to be implemented)
- **Socket.IO Auth** - Bridge authentication (to be implemented)

## 📦 Components

### Modals
- `BlockIPModal` - IP address blocking with validation
- `ExportDataModal` - Data export configuration
- `SettingsPanel` - API key and tier management

### Dashboard
- `QuickActions` - Action buttons with ambient lighting
- `StatusCard` - Metrics with hover glows
- `ThreatChart` - Security trend visualization
- `AlertsTable` - Recent incident table
- `OverwatchDrawer` - Real-time event stream

### Layouts
- `MainLayout` - Header-only layout with Settings gear

## 🎨 Customization

### Ambient Lighting Colors

Edit hover effects in components:

```javascript
// Green for online/success
hover:shadow-[0_0_30px_rgba(34,197,94,0.5)]

// Red for critical/offline
hover:shadow-[0_0_30px_rgba(239,68,68,0.5)]

// Cyan for info/actions
hover:shadow-[0_0_25px_rgba(6,182,212,0.4)]
```

## 📋 Roadmap

- [ ] Connect to FastAPI backend
- [ ] Implement CORS security
- [ ] Add Socket.IO authentication
- [ ] Enable real scan triggers
- [ ] Implement data export with backend
- [ ] Add loading states and error boundaries
- [ ] Responsive design improvements

## 🐛 Known Issues

- Backend integration pending (UI complete, APIs not connected)
- Export currently downloads sample JSON (needs backend connection)
- Scan triggers show alerts (need FastAPI endpoints)

---

**Built by OP-88 for the Sentinyl Security Platform**

📧 Contact: marcwanjohi1@gmail.com
