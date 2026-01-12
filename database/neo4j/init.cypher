// ============================================
// OSINT Autonomous Analyst - Neo4j Graph Schema
// ============================================
// This script initializes the Neo4j graph database with:
// - Node constraints and indexes
// - Assertion-based epistemic modeling
// - Sample data for testing

// ============================================
// 1. CONSTRAINTS (Uniqueness)
// ============================================

CREATE CONSTRAINT person_id IF NOT EXISTS
FOR (n:Person) REQUIRE n.id IS UNIQUE;

CREATE CONSTRAINT org_id IF NOT EXISTS
FOR (n:Organization) REQUIRE n.id IS UNIQUE;

CREATE CONSTRAINT asset_id IF NOT EXISTS
FOR (n:Asset) REQUIRE n.id IS UNIQUE;

CREATE CONSTRAINT event_id IF NOT EXISTS
FOR (n:Event) REQUIRE n.id IS UNIQUE;

CREATE CONSTRAINT campaign_id IF NOT EXISTS
FOR (n:CampaignCluster) REQUIRE n.id IS UNIQUE;

// GOVERNMENT-GRADE: Assertion node for claim modeling
CREATE CONSTRAINT assertion_id IF NOT EXISTS
FOR (n:Assertion) REQUIRE n.id IS UNIQUE;

// ============================================
// 2. INDEXES (Performance)
// ============================================

CREATE INDEX person_name_idx IF NOT EXISTS
FOR (n:Person) ON (n.name);

CREATE INDEX person_risk_idx IF NOT EXISTS
FOR (n:Person) ON (n.risk_score);

CREATE INDEX org_name_idx IF NOT EXISTS
FOR (n:Organization) ON (n.name);

CREATE INDEX org_sanctioned_idx IF NOT EXISTS
FOR (n:Organization) ON (n.sanctioned);

CREATE INDEX asset_type_idx IF NOT EXISTS
FOR (n:Asset) ON (n.asset_type);

CREATE INDEX assertion_source_idx IF NOT EXISTS
FOR (n:Assertion) ON (n.source);

CREATE INDEX assertion_confidence_idx IF NOT EXISTS
FOR (n:Assertion) ON (n.confidence);

// ============================================
// 3. SAMPLE DATA (MVP Testing)
// ============================================

// Sample Person
CREATE (alice:Person {
  id: "person_alice_001",
  name: "Alice Johnson",
  aliases: ["A. Johnson", "AJ"],
  email: ["alice.johnson@example.com"],
  phone: ["+1-555-0100"],
  birth_date: "1985-03-15",
  nationality: ["US"],
  pep_status: false,
  sanctioned: false,
  social_handles: {
    twitter: "@alicejohnson",
    linkedin: "linkedin.com/in/alicejohnson"
  },
  risk_score: 0.35,
  risk_confidence: 0.75,
  source_count: 5,
  last_updated: timestamp(),
  created_date: timestamp()
});

CREATE (bob:Person {
  id: "person_bob_002",
  name: "Robert Chen",
  aliases: ["Bob Chen", "R. Chen"],
  email: [" bob.chen@shadowcorp.com"],
  phone: [],
  birth_date: "1978-11-22",
  nationality: ["CN", "US"],
  pep_status: false,
  sanctioned: false,
  social_handles: {
    telegram: "@bobchen_crypto"
  },
  risk_score: 0.72,
  risk_confidence: 0.68,
  source_count: 12,
  last_updated: timestamp(),
  created_date: timestamp()
});

// Sample Organizations
CREATE (acme:Organization {
  id: "org_acme_001",
  name: "Acme Corporation",
  legal_name: "Acme Corporation Ltd.",
  aliases: ["Acme Corp", "Acme"],
  registration_number: "US-12345678",
  country: "US",
  state: "DE",
  headquarters: "123 Business St, Wilmington, DE",
  sanctioned: false,
  pep: false,
  shell_company_score: 0.15,
  business_lines: ["Technology", "Consulting"],
  risk_score: 0.25,
  risk_dimensions: {
    national_security: 0.10,
    criminal: 0.20,
    financial_crime: 0.15,
    cyber: 0.30,
    reputational: 0.25
  },
  last_updated: timestamp(),
  source_count: 8
});

CREATE (shadow:Organization {
  id: "org_shadow_002",
  name: "Shadow Ventures LLC",
  legal_name: "Shadow Ventures Limited Liability Company",
  aliases: ["ShadowVentures", "SV LLC"],
  registration_number: "MT-98765432",
  country: "MT",  // Malta
  state: "",
  headquarters: "456 Offshore Plaza, Valletta, Malta",
  sanctioned: false,
  pep: false,
  shell_company_score: 0.85,  // HIGH - Likely shell company
  business_lines: ["Holdings"],
  risk_score: 0.78,
  risk_dimensions: {
    national_security: 0.65,
    criminal: 0.80,
    financial_crime: 0.90,
    cyber: 0.70,
    reputational: 0.75
  },
  last_updated: timestamp(),
  source_count: 3
});

// Sample Assets
CREATE (domain:Asset {
  id: "asset_domain_001",
  asset_type: "domain",
  value: "shadowventures.com",
  registrar: "Namecheap",
  registration_date: "2022-01-15",
  first_seen: timestamp(),
  last_seen: timestamp(),
  source_count: 2,
  confidence: 0.95
});

// ============================================
// 4. ASSERTIONS (Government-Grade Epistemic Modeling)
// ============================================

// Assertion 1: Alice is employed by Acme (from LinkedIn)
CREATE (a1:Assertion {
  id: "assertion_001",
  claim_text: "Alice Johnson is employed by Acme Corporation as Senior Analyst",
  source: "LinkedIn",
  source_url: "https://linkedin.com/in/alicejohnson",
  confidence: 0.90,
  timestamp: timestamp(),
  verified: true,
  contradicts: [],
  supports: []
});

// Assertion 2: Bob owns Shadow Ventures (from OpenCorporates - unverified)
CREATE (a2:Assertion {
  id: "assertion_002",
  claim_text: "Robert Chen is beneficial owner of Shadow Ventures LLC",
  source: "OpenCorporates",
  source_url: "https://opencorporates.com/companies/mt/98765432",
  confidence: 0.65,
  timestamp: timestamp(),
  verified: false,
  contradicts: [],
  supports: []
});

// Assertion 3: Shadow Ventures shares infrastructure with known threat actor
CREATE (a3:Assertion {
  id: "assertion_003",
  claim_text: "Shadow Ventures LLC shares IP infrastructure with known APT group",
  source: "Shodan",
  source_url: "https://shodan.io/host/192.0.2.1",
  confidence: 0.72,
  timestamp: timestamp(),
  verified: false,
  contradicts: [],
  supports: ["assertion_002"]  // Supports suspicion about Bob
});

// ============================================
// 5. RELATIONSHIPS
// ============================================

// Traditional relationship (for backward compatibility)
CREATE (alice)-[:EMPLOYED_BY {
  confidence: 0.90,
  title: "Senior Analyst",
  start_date: "2020-06-01",
  source: "LinkedIn",
  timestamp: timestamp()
}]->(acme);

// Assertion-based relationships (GOVERNMENT-GRADE)
CREATE (alice)-[:ASSERTED_BY]->(a1);
CREATE (a1)-[:CLAIMS_RELATION {type: "EMPLOYED_BY"}]->(acme);

CREATE (bob)-[:ASSERTED_BY]->(a2);
CREATE (a2)-[:CLAIMS_RELATION {type: "OWNS"}]->(shadow);

CREATE (shadow)-[:ASSERTED_BY]->(a3);
CREATE (a3)-[:CLAIMS_RELATION {type: "SHARES_INFRASTRUCTURE"}]->(domain);

// Direct relationship (also maintain for query convenience)
CREATE (bob)-[:OWNS {
  confidence: 0.65,
  share_percent: 100.0,
  source: "OpenCorporates",
  timestamp: timestamp()
}]->(shadow);

CREATE (shadow)-[:OWNS]->(domain);

// ============================================
// 6. SAMPLE QUERIES (Verification)
// ============================================

// Query 1: Find all assertions with confidence > 0.7
// MATCH (a:Assertion) WHERE a.confidence > 0.7 RETURN a;

// Query 2: Find entities with high-confidence claims
// MATCH (e)-[:ASSERTED_BY]->(a:Assertion)
// WHERE a.confidence > 0.75
// RETURN e, a;

// Query 3: Find contradicting assertions
// MATCH (a1:Assertion)-[:CONTRADICTS]->(a2:Assertion)
// RETURN a1, a2;

// Query 4: Find high-risk entities within 2 hops of Bob
// MATCH (bob:Person {name: "Robert Chen"})-[*1..2]-(connected)
// WHERE connected.risk_score > 0.5
// RETURN bob, connected;

// Query 5: Evidence timeline for Bob's ownership
// MATCH (bob:Person {name: "Robert Chen"})-[:ASSERTED_BY]->(a:Assertion)
// RETURN a.claim_text, a.source, a.confidence, a.timestamp
// ORDER BY a.timestamp DESC;
