-- Sentinyl Database Schema
-- Digital Risk Protection Platform

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Domains table: Target domains being monitored
CREATE TABLE IF NOT EXISTS domains (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    domain VARCHAR(255) NOT NULL UNIQUE,
    company_name VARCHAR(255),
    priority VARCHAR(20) DEFAULT 'medium', -- low, medium, high, critical
    active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Scan jobs table: Track all scan requests
CREATE TABLE IF NOT EXISTS scan_jobs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    domain_id UUID REFERENCES domains(id) ON DELETE CASCADE,
    job_type VARCHAR(50) NOT NULL, -- typosquat, leak, phishing
    status VARCHAR(20) DEFAULT 'pending', -- pending, processing, completed, failed
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    error_message TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Threats table: Detected typosquatting/phishing domains
CREATE TABLE IF NOT EXISTS threats (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    job_id UUID REFERENCES scan_jobs(id) ON DELETE CASCADE,
    original_domain VARCHAR(255) NOT NULL,
    malicious_domain VARCHAR(255) NOT NULL,
    threat_type VARCHAR(50), -- typosquat, phishing, brand_abuse
    severity VARCHAR(20) DEFAULT 'medium', -- low, medium, high, critical
    ip_address VARCHAR(45),
    nameservers TEXT[],
    whois_data JSONB,
    is_active BOOLEAN DEFAULT TRUE,
    is_verified BOOLEAN DEFAULT FALSE,
    notified BOOLEAN DEFAULT FALSE,
    discovered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    verified_at TIMESTAMP,
    resolved_at TIMESTAMP
);

-- GitHub leaks table: Exposed credentials/secrets
CREATE TABLE IF NOT EXISTS github_leaks (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    job_id UUID REFERENCES scan_jobs(id) ON DELETE CASCADE,
    domain VARCHAR(255) NOT NULL,
    repository_url TEXT NOT NULL,
    repository_name VARCHAR(255),
    file_path TEXT,
    snippet TEXT,
    leak_type VARCHAR(50), -- password, api_key, secret, token, credentials
    severity VARCHAR(20) DEFAULT 'high',
    is_public BOOLEAN DEFAULT TRUE,
    notified BOOLEAN DEFAULT FALSE,
    discovered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    resolved_at TIMESTAMP
);

-- Notifications table: Track sent alerts
CREATE TABLE IF NOT EXISTS notifications (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    threat_id UUID,
    leak_id UUID,
    notification_type VARCHAR(50), -- slack, email, webhook
    recipient VARCHAR(255),
    message TEXT,
    sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    status VARCHAR(20) DEFAULT 'sent' -- sent, failed, pending
);

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_domains_active ON domains(active);
CREATE INDEX IF NOT EXISTS idx_scan_jobs_status ON scan_jobs(status);
CREATE INDEX IF NOT EXISTS idx_scan_jobs_created ON scan_jobs(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_threats_severity ON threats(severity);
CREATE INDEX IF NOT EXISTS idx_threats_notified ON threats(notified) WHERE notified = FALSE;
CREATE INDEX IF NOT EXISTS idx_threats_domain ON threats(malicious_domain);
CREATE INDEX IF NOT EXISTS idx_leaks_severity ON github_leaks(severity);
CREATE INDEX IF NOT EXISTS idx_leaks_notified ON github_leaks(notified) WHERE notified = FALSE;

-- Insert sample domain for testing
INSERT INTO domains (domain, company_name, priority) 
VALUES ('example.com', 'Example Corp', 'high')
ON CONFLICT (domain) DO NOTHING;

-- Trigger to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_domains_updated_at BEFORE UPDATE ON domains
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
