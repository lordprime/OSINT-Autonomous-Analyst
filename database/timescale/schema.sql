-- ============================================
-- OSINT Autonomous Analyst - TimescaleDB Schema
-- ============================================
-- Temporal and geospatial data storage
-- Optimized for timeline queries and anomaly detection

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS timescaledb;
CREATE EXTENSION IF NOT EXISTS postgis;

-- ============================================
-- 1. EVENT TIMELINE TABLE
-- ============================================

CREATE TABLE events (
    event_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    timestamp TIMESTAMPTZ NOT NULL,
    event_type VARCHAR(50) NOT NULL,  -- 'collection', 'entity_update', 'hypothesis_test', etc.
    investigation_id UUID,
    entity_id VARCHAR(255),
    entity_type VARCHAR(50),
    
    -- Event details
    description TEXT,
    source VARCHAR(255),
    confidence DOUBLE PRECISION CHECK (confidence >= 0.0 AND confidence <= 1.0),
    
    -- Geospatial data
    location_name VARCHAR(255),
    coordinates GEOGRAPHY(POINT, 4326),  -- PostGIS point
    
    -- Metadata
    metadata JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Convert to hypertable (TimescaleDB)
SELECT create_hypertable('events', 'timestamp');

-- Indexes
CREATE INDEX idx_events_investigation ON events(investigation_id, timestamp DESC);
CREATE INDEX idx_events_entity ON events(entity_id, timestamp DESC);
CREATE INDEX idx_events_type ON events(event_type);
CREATE INDEX idx_events_location ON events USING GIST(coordinates);

-- ============================================
-- 2. ACTIVITY TRACKING TABLE
-- ============================================

CREATE TABLE entity_activity (
    id BIGSERIAL,
    timestamp TIMESTAMPTZ NOT NULL,
    entity_id VARCHAR(255) NOT NULL,
    entity_type VARCHAR(50) NOT NULL,
    
    -- Activity metrics
    activity_type VARCHAR(50),  -- 'post', 'transaction', 'login', 'communication'
    platform VARCHAR(100),  -- 'twitter', 'reddit', 'telegram', etc.
    activity_count INTEGER DEFAULT 1,
    
    -- Engagement metrics
    engagement_score DOUBLE PRECISION,
    reach_estimate INTEGER,
    
    -- Context
    content_hash VARCHAR(64),  -- SHA-256 of content
    metadata JSONB,
    
    PRIMARY KEY (id, timestamp)
);

-- Convert to hypertable
SELECT create_hypertable('entity_activity', 'timestamp');

-- Indexes
CREATE INDEX idx_activity_entity ON entity_activity(entity_id, timestamp DESC);
CREATE INDEX idx_activity_platform ON entity_activity(platform);
CREATE INDEX idx_activity_type ON entity_activity(activity_type);

-- ============================================
-- 3. GEOSPATIAL TRACKING TABLE
-- ============================================

CREATE TABLE geospatial_events (
    id BIGSERIAL,
    timestamp TIMESTAMPTZ NOT NULL,
    entity_id VARCHAR(255) NOT NULL,
    
    -- Location data
    location_name VARCHAR(255),
    coordinates GEOGRAPHY(POINT, 4326),
    accuracy_meters DOUBLE PRECISION,
    
    -- Event details
    event_type VARCHAR(50),  -- 'check-in', 'photo', 'ip_location', 'flight', 'ship'
    source VARCHAR(100),
    confidence DOUBLE PRECISION,
    
    -- Travel analysis
    previous_location_id BIGINT,  -- Reference to previous location
    travel_time_seconds INTEGER,
    travel_distance_meters DOUBLE PRECISION,
    impossible_travel BOOLEAN DEFAULT FALSE,
    
    metadata JSONB,
    
    PRIMARY KEY (id, timestamp)
);

-- Convert to hypertable
SELECT create_hypertable('geospatial_events', 'timestamp');

-- Indexes
CREATE INDEX idx_geo_entity ON geospatial_events(entity_id, timestamp DESC);
CREATE INDEX idx_geo_location ON geospatial_events USING GIST(coordinates);
CREATE INDEX idx_geo_impossible_travel ON geospatial_events(impossible_travel) WHERE impossible_travel = TRUE;

-- ============================================
-- 4. AUDIT LOG TABLE (Immutable)
-- ============================================

CREATE TABLE audit_log (
    log_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    -- User context
    user_id VARCHAR(255) NOT NULL,
    user_role VARCHAR(50),
    clearance_level VARCHAR(50),
    
    -- Action details
    action_type VARCHAR(50) NOT NULL,  -- 'query', 'collection', 'hypothesis_test', 'export', 'denied_action'
    investigation_id UUID,
    target VARCHAR(500),  -- URL, entity ID, query text, etc.
    
    -- Request details
    request_payload JSONB,
    response_status VARCHAR(50),
    
    -- Compliance
    justification TEXT,
    policy_ids TEXT[],
    
    -- Denial tracking (GOVERNMENT-GRADE)
    is_denied BOOLEAN DEFAULT FALSE,
    denial_reason TEXT,
    denial_policy_id VARCHAR(100),
    
    -- Metadata
    metadata JSONB
);

-- Convert to hypertable
SELECT create_hypertable('audit_log', 'timestamp');

-- Indexes
CREATE INDEX idx_audit_user ON audit_log(user_id, timestamp DESC);
CREATE INDEX idx_audit_investigation ON audit_log(investigation_id, timestamp DESC);
CREATE INDEX idx_audit_action ON audit_log(action_type);
CREATE INDEX idx_audit_denied ON audit_log(is_denied) WHERE is_denied = TRUE;

-- Make audit log append-only (immutable)
CREATE OR REPLACE FUNCTION prevent_audit_modification()
RETURNS TRIGGER AS $$
BEGIN
    IF TG_OP = 'UPDATE' OR TG_OP = 'DELETE' THEN
        RAISE EXCEPTION 'Audit log is immutable. Cannot modify or delete records.';
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER audit_immutable
BEFORE UPDATE OR DELETE ON audit_log
FOR EACH ROW EXECUTE FUNCTION prevent_audit_modification();

-- ============================================
-- 5. RISK SCORE HISTORY TABLE
-- ============================================

CREATE TABLE risk_score_history (
    id BIGSERIAL,
    timestamp TIMESTAMPTZ NOT NULL,
    entity_id VARCHAR(255) NOT NULL,
    entity_type VARCHAR(50) NOT NULL,
    
    -- Risk scores
    overall_score DOUBLE PRECISION,
    national_security DOUBLE PRECISION,
    criminal DOUBLE PRECISION,
    financial_crime DOUBLE PRECISION,
    cyber DOUBLE PRECISION,
    reputational DOUBLE PRECISION,
    
    -- Confidence
    confidence DOUBLE PRECISION,
    
    -- Evidence
    evidence_count INTEGER,
    primary_evidence_source VARCHAR(255),
    
    -- Reasoning
    explanation TEXT,
    
    PRIMARY KEY (id, timestamp)
);

-- Convert to hypertable
SELECT create_hypertable('risk_score_history', 'timestamp');

-- Index
CREATE INDEX idx_risk_entity ON risk_score_history(entity_id, timestamp DESC);

-- ============================================
-- 6. CONTINUOUS AGGREGATES (Pre-computed Analytics)
-- ============================================

-- Daily activity summary per entity
CREATE MATERIALIZED VIEW entity_daily_activity
WITH (timescaledb.continuous) AS
SELECT
    entity_id,
    entity_type,
    time_bucket('1 day', timestamp) AS day,
    COUNT(*) AS activity_count,
    AVG(engagement_score) AS avg_engagement,
    SUM(reach_estimate) AS total_reach,
    array_agg(DISTINCT platform) AS platforms_used
FROM entity_activity
GROUP BY entity_id, entity_type, day;

-- Refresh policy (every 1 hour)
SELECT add_continuous_aggregate_policy('entity_daily_activity',
    start_offset => INTERVAL '7 days',
    end_offset => INTERVAL '1 hour',
    schedule_interval => INTERVAL '1 hour');

-- ============================================
-- 7. HELPER FUNCTIONS
-- ============================================

-- Function: Detect impossible travel
CREATE OR REPLACE FUNCTION detect_impossible_travel()
RETURNS TRIGGER AS $$
DECLARE
    prev_location RECORD;
    distance_meters DOUBLE PRECISION;
    time_diff_seconds INTEGER;
    max_speed_mps DOUBLE PRECISION := 250;  -- ~900 km/h (commercial flight)
BEGIN
    -- Get previous location
    SELECT * INTO prev_location
    FROM geospatial_events
    WHERE entity_id = NEW.entity_id
      AND id < NEW.id
    ORDER BY timestamp DESC
    LIMIT 1;
    
    IF FOUND THEN
        -- Calculate distance and time
        distance_meters := ST_Distance(
            prev_location.coordinates::geometry,
            NEW.coordinates::geometry
        );
        time_diff_seconds := EXTRACT(EPOCH FROM (NEW.timestamp - prev_location.timestamp));
        
        -- Check if travel speed exceeds maximum
        IF time_diff_seconds > 0 AND (distance_meters / time_diff_seconds) > max_speed_mps THEN
            NEW.impossible_travel := TRUE;
            NEW.previous_location_id := prev_location.id;
            NEW.travel_distance_meters := distance_meters;
            NEW.travel_time_seconds := time_diff_seconds;
        END IF;
    END IF;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger for impossible travel detection
CREATE TRIGGER check_impossible_travel
BEFORE INSERT ON geospatial_events
FOR EACH ROW EXECUTE FUNCTION detect_impossible_travel();

-- ============================================
-- 8. SAMPLE DATA (Testing)
-- ============================================

-- Sample event
INSERT INTO events (timestamp, event_type, investigation_id, description, source, confidence)
VALUES (NOW(), 'entity_discovered', '550e8400-e29b-41d4-a716-446655440000', 
        'New entity discovered via Twitter scraping', 'twitter_agent', 0.85);

-- Sample audit log entry
INSERT INTO audit_log (user_id, user_role, clearance_level, action_type, investigation_id, 
                       target, justification, is_denied)
VALUES ('user_analyst_001', 'analyst', 'secret', 'query', 
        '550e8400-e29b-41d4-a716-446655440000',
        'Find owners of Acme Corp', 'Ongoing corporate investigation', FALSE);

-- Sample denied action (GOVERNMENT-GRADE)
INSERT INTO audit_log (user_id, user_role, clearance_level, action_type, target,
                       justification, is_denied, denial_reason, denial_policy_id)
VALUES ('user_analyst_002', 'analyst', 'confidential', 'collection',
        'https://eu-citizen-data.example.com',
        'Attempted PII collection', TRUE, 
        'PII collection in EU prohibited by GDPR policy', 'POLICY_GDPR_001');

-- ============================================
-- 9. RETENTION POLICIES
-- ============================================

-- Keep event data for 7 years (government requirement)
SELECT add_retention_policy('events', INTERVAL '7 years');

-- Keep activity data for 2 years
SELECT add_retention_policy('entity_activity', INTERVAL '2 years');

-- Keep audit logs indefinitely (no retention policy)

-- ============================================
-- 10. PERFORMANCE TUNING
-- ============================================

-- Enable compression for older data
ALTER TABLE events SET (
    timescaledb.compress,
    timescaledb.compress_segmentby = 'investigation_id'
);

SELECT add_compression_policy('events', INTERVAL '30 days');

-- Vacuum and analyze
VACUUM ANALYZE events;
VACUUM ANALYZE entity_activity;
VACUUM ANALYZE geospatial_events;
VACUUM ANALYZE audit_log;
