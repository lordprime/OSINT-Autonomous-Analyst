// ============================================
// Extended Schema for API Integration
// ============================================

// Investigation constraints
CREATE CONSTRAINT investigation_id IF NOT EXISTS
FOR (n:Investigation) REQUIRE n.id IS UNIQUE;

CREATE INDEX investigation_created_by IF NOT EXISTS
FOR (n:Investigation) ON (n.created_by);

CREATE INDEX investigation_status IF NOT EXISTS
FOR (n:Investigation) ON (n.status);

CREATE INDEX investigation_created_at IF NOT EXISTS
FOR (n:Investigation) ON (n.created_at);

// Entity constraints  
CREATE CONSTRAINT entity_id IF NOT EXISTS
FOR (n:Entity) REQUIRE n.id IS UNIQUE;

CREATE INDEX entity_name IF NOT EXISTS
FOR (n:Entity) ON (n.name);

CREATE INDEX entity_type IF NOT EXISTS
FOR (n:Entity) ON (n.type);

CREATE INDEX entity_confidence IF NOT EXISTS
FOR (n:Entity) ON (n.confidence);

CREATE INDEX entity_created_at IF NOT EXISTS
FOR (n:Entity) ON (n.created_at);

// Collection Job constraints
CREATE CONSTRAINT collection_job_id IF NOT EXISTS
FOR (n:CollectionJob) REQUIRE n.id IS UNIQUE;

CREATE INDEX collection_job_status IF NOT EXISTS
FOR (n:CollectionJob) ON (n.status);

// Hypothesis constraints
CREATE CONSTRAINT hypothesis_id IF NOT EXISTS
FOR (n:Hypothesis) REQUIRE n.id IS UNIQUE;

CREATE INDEX hypothesis_confidence IF NOT EXISTS
FOR (n:Hypothesis) ON (n.confidence);

// Plan constraints
CREATE CONSTRAINT plan_id IF NOT EXISTS
FOR (n:Plan) REQUIRE n.id IS UNIQUE;
