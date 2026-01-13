-- ============================================
-- OSINT Autonomous Analyst - Extended Schema
-- Additional tables for API functionality
-- ============================================

-- ============================================
-- Investigations Table
-- ============================================
CREATE TABLE IF NOT EXISTS investigations (
    id UUID PRIMARY KEY,
    name VARCHAR(200) NOT NULL,
    target VARCHAR(500) NOT NULL,
    goal TEXT NOT NULL,
    status VARCHAR(50) NOT NULL DEFAULT 'created',
    created_by VARCHAR(100) NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
    completed_at TIMESTAMP,
    metadata JSONB DEFAULT '{}'::jsonb
);

CREATE INDEX idx_investigations_created_by ON investigations(created_by);
CREATE INDEX idx_investigations_status ON investigations(status);
CREATE INDEX idx_investigations_created_at ON investigations(created_at DESC);

-- ============================================
-- Collection Jobs Table
-- ============================================
CREATE TABLE IF NOT EXISTS collection_jobs (
    id UUID PRIMARY KEY,
    investigation_id UUID NOT NULL REFERENCES investigations(id) ON DELETE CASCADE,
    agent_type VARCHAR(50) NOT NULL,
    query VARCHAR(500) NOT NULL,
    status VARCHAR(50) NOT NULL DEFAULT 'pending',
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    items_collected INTEGER DEFAULT 0,
    entities_discovered INTEGER DEFAULT 0,
    errors TEXT[],
    metadata JSONB DEFAULT '{}'::jsonb
);

CREATE INDEX idx_collection_jobs_investigation ON collection_jobs(investigation_id);
CREATE INDEX idx_collection_jobs_status ON collection_jobs(status);
CREATE INDEX idx_collection_jobs_created_at ON collection_jobs(created_at DESC);

-- Convert to hypertable for time-series optimization
SELECT create_hypertable('collection_jobs', 'created_at',
    chunk_time_interval => INTERVAL '7 days',
    if_not_exists => TRUE
);

-- ============================================
-- Timeline Events Table
-- ============================================
CREATE TABLE IF NOT EXISTS timeline_events (
    id UUID DEFAULT gen_random_uuid(),
    investigation_id UUID NOT NULL,
    timestamp TIMESTAMP NOT NULL DEFAULT NOW(),
    event_type VARCHAR(100) NOT NULL,
    description TEXT NOT NULL,
    entity_ids UUID[],
    metadata JSONB DEFAULT '{}'::jsonb,
    PRIMARY KEY (timestamp, id)
);

CREATE INDEX idx_timeline_investigation ON timeline_events(investigation_id, timestamp DESC);
CREATE INDEX idx_timeline_event_type ON timeline_events(event_type);

-- Convert to hypertable
SELECT create_hypertable('timeline_events', 'timestamp',
    chunk_time_interval => INTERVAL '30 days',
    if_not_exists => TRUE
);

-- ============================================
-- Helper Functions
-- ============================================

-- Function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Trigger for investigations table
DROP TRIGGER IF EXISTS update_investigations_updated_at ON investigations;
CREATE TRIGGER update_investigations_updated_at
    BEFORE UPDATE ON investigations
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();
