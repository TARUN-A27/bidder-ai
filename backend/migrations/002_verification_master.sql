SET SQLBLANKLINES ON
WHENEVER SQLERROR EXIT SQL.SQLCODE
WHENEVER OSERROR EXIT FAILURE

CREATE TABLE scoring_profiles (
    id                  VARCHAR2(36) PRIMARY KEY,
    tender_id           VARCHAR2(36) NOT NULL,
    profile_code        VARCHAR2(100) NOT NULL,
    profile_name        VARCHAR2(500) NOT NULL,
    total_weight        NUMBER(6,2) NOT NULL,
    active              NUMBER(1) DEFAULT 1 NOT NULL,
    created_at          TIMESTAMP WITH TIME ZONE DEFAULT SYSTIMESTAMP NOT NULL,

    CONSTRAINT fk_scoring_profile_tender
        FOREIGN KEY (tender_id)
        REFERENCES tenders(id)
        ON DELETE CASCADE,

    CONSTRAINT uq_scoring_profile
        UNIQUE (tender_id, profile_code),

    CONSTRAINT chk_scoring_profile_active
        CHECK (active IN (0,1))
);

CREATE TABLE scoring_status_credits (
    id                  VARCHAR2(36) PRIMARY KEY,
    scoring_profile_id  VARCHAR2(36) NOT NULL,
    status_code         VARCHAR2(30) NOT NULL,
    credit_factor       NUMBER(6,4) NOT NULL,
    exclude_from_total  NUMBER(1) DEFAULT 0 NOT NULL,

    CONSTRAINT fk_status_credit_profile
        FOREIGN KEY (scoring_profile_id)
        REFERENCES scoring_profiles(id)
        ON DELETE CASCADE,

    CONSTRAINT uq_status_credit
        UNIQUE (scoring_profile_id, status_code),

    CONSTRAINT chk_status_credit_exclude
        CHECK (exclude_from_total IN (0,1))
);

CREATE TABLE risk_bands (
    id                  VARCHAR2(36) PRIMARY KEY,
    scoring_profile_id  VARCHAR2(36) NOT NULL,
    risk_level          VARCHAR2(30) NOT NULL,
    min_score           NUMBER(6,2),
    max_score           NUMBER(6,2),
    min_inclusive       NUMBER(1) DEFAULT 1 NOT NULL,
    max_inclusive       NUMBER(1) DEFAULT 0 NOT NULL,
    display_order       NUMBER NOT NULL,

    CONSTRAINT fk_risk_band_profile
        FOREIGN KEY (scoring_profile_id)
        REFERENCES scoring_profiles(id)
        ON DELETE CASCADE,

    CONSTRAINT uq_risk_band
        UNIQUE (scoring_profile_id, risk_level),

    CONSTRAINT chk_risk_band_level
        CHECK (risk_level IN ('LOW','MEDIUM','HIGH','CRITICAL')),

    CONSTRAINT chk_risk_band_min_inc
        CHECK (min_inclusive IN (0,1)),

    CONSTRAINT chk_risk_band_max_inc
        CHECK (max_inclusive IN (0,1))
);

CREATE TABLE risk_override_rules (
    id                  VARCHAR2(36) PRIMARY KEY,
    scoring_profile_id  VARCHAR2(36) NOT NULL,
    override_code       VARCHAR2(100) NOT NULL,
    description         CLOB NOT NULL,
    minimum_risk_level  VARCHAR2(30) NOT NULL,
    trigger_json        CLOB NOT NULL,
    active              NUMBER(1) DEFAULT 1 NOT NULL,

    CONSTRAINT fk_risk_override_profile
        FOREIGN KEY (scoring_profile_id)
        REFERENCES scoring_profiles(id)
        ON DELETE CASCADE,

    CONSTRAINT uq_risk_override
        UNIQUE (scoring_profile_id, override_code),

    CONSTRAINT chk_override_risk_level
        CHECK (minimum_risk_level IN ('LOW','MEDIUM','HIGH','CRITICAL')),

    CONSTRAINT chk_override_trigger_json
        CHECK (trigger_json IS JSON),

    CONSTRAINT chk_override_active
        CHECK (active IN (0,1))
);

CREATE TABLE tender_required_documents (
    id                  VARCHAR2(36) PRIMARY KEY,
    tender_id           VARCHAR2(36) NOT NULL,
    document_code       VARCHAR2(100) NOT NULL,
    document_name       VARCHAR2(500) NOT NULL,
    description         CLOB,
    mandatory           NUMBER(1) DEFAULT 1 NOT NULL,
    conditional         NUMBER(1) DEFAULT 0 NOT NULL,
    condition_text      CLOB,
    active              NUMBER(1) DEFAULT 1 NOT NULL,

    CONSTRAINT fk_required_doc_tender
        FOREIGN KEY (tender_id)
        REFERENCES tenders(id)
        ON DELETE CASCADE,

    CONSTRAINT uq_required_doc
        UNIQUE (tender_id, document_code),

    CONSTRAINT chk_required_doc_mandatory
        CHECK (mandatory IN (0,1)),

    CONSTRAINT chk_required_doc_conditional
        CHECK (conditional IN (0,1)),

    CONSTRAINT chk_required_doc_active
        CHECK (active IN (0,1))
);

CREATE TABLE requirement_document_rules (
    id                      VARCHAR2(36) PRIMARY KEY,
    requirement_id          VARCHAR2(36) NOT NULL,
    required_document_id    VARCHAR2(36) NOT NULL,
    evidence_role           VARCHAR2(100),
    mandatory_evidence      NUMBER(1) DEFAULT 1 NOT NULL,

    CONSTRAINT fk_req_doc_rule_requirement
        FOREIGN KEY (requirement_id)
        REFERENCES tender_requirements(id)
        ON DELETE CASCADE,

    CONSTRAINT fk_req_doc_rule_document
        FOREIGN KEY (required_document_id)
        REFERENCES tender_required_documents(id)
        ON DELETE CASCADE,

    CONSTRAINT uq_req_doc_rule
        UNIQUE (requirement_id, required_document_id),

    CONSTRAINT chk_req_doc_rule_mandatory
        CHECK (mandatory_evidence IN (0,1))
);

CREATE TABLE requirement_verification_sources (
    id                      VARCHAR2(36) PRIMARY KEY,
    requirement_id          VARCHAR2(36) NOT NULL,
    verification_source_id  VARCHAR2(36) NOT NULL,
    priority_order          NUMBER DEFAULT 1 NOT NULL,
    authoritative           NUMBER(1) DEFAULT 1 NOT NULL,

    CONSTRAINT fk_req_source_requirement
        FOREIGN KEY (requirement_id)
        REFERENCES tender_requirements(id)
        ON DELETE CASCADE,

    CONSTRAINT fk_req_source_source
        FOREIGN KEY (verification_source_id)
        REFERENCES verification_sources(id)
        ON DELETE CASCADE,

    CONSTRAINT uq_req_source
        UNIQUE (requirement_id, verification_source_id),

    CONSTRAINT chk_req_source_authoritative
        CHECK (authoritative IN (0,1))
);

CREATE INDEX idx_scoring_profile_tender
ON scoring_profiles(tender_id);

CREATE INDEX idx_status_credit_profile
ON scoring_status_credits(scoring_profile_id);

CREATE INDEX idx_risk_band_profile
ON risk_bands(scoring_profile_id);

CREATE INDEX idx_risk_override_profile
ON risk_override_rules(scoring_profile_id);

CREATE INDEX idx_required_doc_tender
ON tender_required_documents(tender_id);

CREATE INDEX idx_req_doc_requirement
ON requirement_document_rules(requirement_id);

CREATE INDEX idx_req_source_requirement
ON requirement_verification_sources(requirement_id);

COMMIT;
