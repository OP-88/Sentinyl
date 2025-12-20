# Sentinyl Dashboard - Setup Guide

## Quick Start

### 1. Frontend Setup

```bash
cd /home/marc/Verba-mvp/Sentinyl/sentinyl-overwatch

# Copy environment template
cp .env.example .env

# Install dependencies (if not already installed)
npm install

# Start development server
npm run dev
```

The frontend will be available at `http://localhost:5173`

### 2. Backend API Setup

```bash
cd /home/marc/Verba-mvp/Sentinyl

# Copy environment template (if not exists)
cp .env.example .env

# Edit .env and configure:
# - ALLOWED_ORIGINS=http://localhost:5173,http://localhost:3000
# - Database credentials
# - Redis URL
# - Other services as needed

# Start the backend
python -m backend.main
```

The backend API will be available at `http://localhost:8000`

### 3. Socket.IO Bridge Setup

```bash
cd /home/marc/Verba-mvp/Sentinyl/sentinyl-overwatch/bridge

# Copy environment template
cp .env.example .env

# Edit .env and configure:
# - BACKEND_API_URL=http://localhost:8000
# - ALLOWED_ORIGINS=http://localhost:5173

# Install dependencies
npm install

# Start bridge server
npm start
```

The bridge will be available at `http://localhost:3000`

## Configuration

### Frontend (.env)

```env
VITE_API_URL=http://localhost:8000
VITE_BRIDGE_URL=http://localhost:3000
VITE_ENABLE_DEBUG=false
```

### Backend (.env)

```env
ALLOWED_ORIGINS=http://localhost:5173,http://localhost:3000
DATABASE_URL=postgresql://sentinyl:password@localhost:5432/sentinyldb
REDIS_URL=redis://localhost:6379/0
```

### Bridge (.env)

```env
PORT=3000
BACKEND_API_URL=http://localhost:8000
ALLOWED_ORIGINS=http://localhost:5173
RATE_LIMIT_POINTS=100
RATE_LIMIT_DURATION=60
```

## Features Implemented

### ✅ Environment Configuration
- Frontend environment variables for API URLs
- Backend CORS configuration from environment
- Bridge authentication and security settings

### ✅ CORS Security
- **Backend**: Restricted origins from wildcard (*) to environment-based whitelist
- **Bridge**: Environment-based origin restriction for Socket.IO
- Both support comma-separated lists for multiple origins

### ✅ Real API Integration
- Dashboard stats connected to `/stats` endpoint
- Scan functionality integrated with `/scan` endpoint
- Block IP connected to `/guard/block-ip` endpoint
- Export data functionality with backend API
- Automatic data refresh and loading states

### ✅ Error Handling
- Global `ErrorBoundary` component for React errors
- Toast notification system for user feedback
- `useApi` hook with automatic retry logic (exponential backoff)
- User-friendly error messages for all API errors
- Loading skeletons for async operations
- Network error detection and handling

### ✅ Socket.IO Security
- **API Key Authentication**: Validates API keys with backend `/auth/me` endpoint
- **Rate Limiting**: 100 events per minute per connection (configurable)
- **Connection Timeout**: 30-second idle timeout with activity-based reset
- **Authenticated Sessions**: Tracks user info and tier for each connection
- **Error Handling**: Graceful disconnection for invalid authentication

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    User's Browser                           │
│                                                              │
│  ┌────────────────────────────────────────────────────┐    │
│  │   React Dashboard (http://localhost:5173)          │    │
│  │   - Environment: VITE_API_URL, VITE_BRIDGE_URL    │    │
│  │   - ErrorBoundary + ToastProvider                  │    │
│  │   - useApi hooks with retry logic                  │    │
│  └─────────┬────────────────────────────┬─────────────┘    │
│            │                             │                   │
└────────────┼─────────────────────────────┼──────────────────┘
             │ HTTP (axios)                │ WebSocket
             │ Bearer Token Auth           │ API Key Auth
             ▼                             ▼
    ┌────────────────┐          ┌──────────────────────┐
    │  FastAPI       │◄─────────│  Socket.IO Bridge    │
    │  Backend       │  Validate│  (localhost:3000)    │
    │  (localhost:   │  API Key │                      │
    │   8000)        │          │  - Authentication    │
    │                │          │  - Rate Limiting     │
    │ - CORS: Env    │          │  - Idle Timeout      │
    │   Based        │          │  - CORS: Env Based   │
    │ - /stats       │          │                      │
    │ - /scan        │          │                      │
    │ - /guard/*     │          │                      │
    │ - /auth/me     │          │                      │
    └────────────────┘          └──────────────────────┘
             │                             │
             │                             │
             ▼                             ▼
    ┌────────────────┐          ┌──────────────────────┐
    │  PostgreSQL    │          │  Redis Queue         │
    │  Database      │          │                      │
    └────────────────┘          └──────────────────────┘
```

## Testing

### 1. Test Backend CORS

```bash
# Should succeed (allowed origin)
curl -H "Origin: http://localhost:5173" http://localhost:8000/health -v

# Should fail (disallowed origin)
curl -H "Origin: http://evil.com" http://localhost:8000/health -v
```

### 2. Test API Integration

1. Start all three services (frontend, backend, bridge)
2. Open browser to `http://localhost:5173`
3. Check browser console for any errors
4. Verify stats cards show real data (not 0 or loading forever)
5. Click "Start Scan" - should prompt for domain and submit to backend
6. Check backend logs for scan request

### 3. Test Socket.IO Authentication

1. Open browser console
2. Navigate to Network tab → WS filter
3. Look for Socket.IO connection
4. Should see "auth" in connection parameters
5. Check bridge server logs for "Authenticated client connected"

### 4. Test Error Handling

1. Stop backend server
2. Refresh dashboard
3. Should see error toast notifications (not raw errors)
4. Should see retry buttons on failed components
5. Start backend again and click retry - should work

## API Key Setup

To connect the dashboard, you need an API key:

1. **Register a user** (if not exists):
   ```bash
   curl -X POST http://localhost:8000/auth/register \
     -H "Content-Type: application/json" \
     -d '{"email": "admin@example.com", "name": "Admin User"}'
   ```
   
   **Copy the API key from the response!** It's only shown once.

2. **Store API key** in `localStorage`:
   - Open browser console
   - Run: `localStorage.setItem('sentinyl_api_key', 'YOUR_API_KEY_HERE')`
   - Refresh the page

3. The dashboard will now authenticate all API calls and Socket.IO connections with this key.

## Troubleshooting

### "Network Error" on Dashboard

- **Check**: Is the backend running on port 8000?
- **Check**: Is `VITE_API_URL` correctly set in frontend `.env`?
- **Check**: Did you copy `.env.example` to `.env`?

### Socket.IO Not Connecting

- **Check**: Is the bridge server running on port 3000?
- **Check**: Is `VITE_BRIDGE_URL` correctly set?
- **Check**: Do you have a valid API key in `localStorage`?
- **Check**: Bridge logs for authentication errors

### CORS Errors

- **Check**: Backend `.env` has `ALLOWED_ORIGINS=http://localhost:5173`
- **Check**: Bridge `.env` has `ALLOWED_ORIGINS=http://localhost:5173`
- **Check**: No trailing slashes in origin URLs

### Stats Not Loading

- **Check**: Backend `/stats` endpoint is working: `curl http://localhost:8000/stats`
- **Check**: Database is running and seeded with data
- **Check**: API key is valid and has proper permissions

## Next Steps

1. ✅ Environment configuration
2. ✅ CORS security
3. ✅ Real API integration
4. ✅ Error handling
5. ✅ Socket.IO authentication
6. 🔄 Connect AlertsTable to real alerts endpoint
7. 🔄 Add TerminalLog authentication
8. 🔄 Testing and validation
