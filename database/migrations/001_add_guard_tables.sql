-- Sentinyl Guard database schema migration
-- Add tables for agent registration and behavioral anomaly tracking

-- Guard Agents (VPS instances running Sentinyl Guard agent)
CREATE TABLE IF NOT EXISTS guard_agents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    hostname VARCHAR(255) NOT NULL,
    ip_address VARCHAR(45),
    os_info VARCHAR(255),
    last_heartbeat TIMESTAMP,
    active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_guard_agents_active ON guard_agents(active);
CREATE INDEX IF NOT EXISTS idx_guard_agents_heartbeat ON guard_agents(last_heartbeat);

-- Guard Events (Behavioral anomaly events)
CREATE TABLE IF NOT EXISTS guard_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    agent_id UUID REFERENCES guard_agents(id) ON DELETE CASCADE,
    anomaly_type VARCHAR(50) NOT NULL,
    severity VARCHAR(20) DEFAULT 'high',
    target_ip VARCHAR(45),
    target_country VARCHAR(100),
    process_name VARCHAR(255),
    details JSONB,
    countdown_started_at TIMESTAMP,
    countdown_expires_at TIMESTAMP,
    admin_response VARCHAR(20),
    admin_user VARCHAR(255),
    responded_at TIMESTAMP,
    blocked BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_guard_events_agent ON guard_events(agent_id);
CREATE INDEX IF NOT EXISTS idx_guard_events_pending ON guard_events(admin_response) WHERE admin_response IS NULL;
CREATE INDEX IF NOT EXISTS idx_guard_events_countdown ON guard_events(countdown_expires_at);
CREATE INDEX IF NOT EXISTS idx_guard_events_severity ON guard_events(severity);
