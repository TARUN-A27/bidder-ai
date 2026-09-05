SET SQLBLANKLINES ON
WHENEVER SQLERROR EXIT SQL.SQLCODE
WHENEVER OSERROR EXIT FAILURE

CREATE TABLE buyers (
    id                  VARCHAR2(36) PRIMARY KEY,
    name                VARCHAR2(500) NOT NULL,
    ministry            VARCHAR2(500),
    department          VARCHAR2(500),
    organisation        VARCHAR2(500),
    office              VARCHAR2(500),
    address             CLOB,
    is_synthetic        NUMBER(1) DEFAULT 0 NOT NULL,
    created_at          TIMESTAMP WITH TIME ZONE DEFAULT SYSTIMESTAMP NOT NULL,
    CONSTRAINT chk_buyers_synthetic CHECK (is_synthetic IN (0,1))
);

CREATE TABLE tenders (
    id                                  VARCHAR2(36) PRIMARY KEY,
    buyer_id                            VARCHAR2(36),
    dataset_id                          VARCHAR2(100),
    bid_number                          VARCHAR2(255) NOT NULL,
    title                               VARCHAR2(1000) NOT NULL,
    category                            VARCHAR2(1000),
    quantity                            NUMBER,
    estimated_value_inr                 NUMBER(18,2),
    bid_date                            DATE,
    bid_end_at                          TIMESTAMP WITH TIME ZONE,
    bid_opening_at                      TIMESTAMP WITH TIME ZONE,
    offer_validity_days                 NUMBER,
    offer_valid_through                 DATE,
    oem_authorization_required_through  DATE,
    delivery_days                       NUMBER,
    installation_days                   NUMBER,
    warranty_years                      NUMBER,
    evaluation_method                   VARCHAR2(200),
    status                              VARCHAR2(50) DEFAULT 'DRAFT',
    human_final_decision_required       NUMBER(1) DEFAULT 1 NOT NULL,
    is_synthetic                        NUMBER(1) DEFAULT 0 NOT NULL,
    created_at                          TIMESTAMP WITH TIME ZONE DEFAULT SYSTIMESTAMP NOT NULL,
    updated_at                          TIMESTAMP WITH TIME ZONE DEFAULT SYSTIMESTAMP NOT NULL,

    CONSTRAINT fk_tenders_buyer
        FOREIGN KEY (buyer_id) REFERENCES buyers(id),

    CONSTRAINT uq_tenders_bid_number UNIQUE (bid_number),
    CONSTRAINT chk_tenders_human_decision CHECK (human_final_decision_required IN (0,1)),
    CONSTRAINT chk_tenders_synthetic CHECK (is_synthetic IN (0,1))
);

CREATE TABLE tender_documents (
    id              VARCHAR2(36) PRIMARY KEY,
    tender_id       VARCHAR2(36) NOT NULL,
    document_code   VARCHAR2(100),
    document_type   VARCHAR2(150),
    file_name       VARCHAR2(1000) NOT NULL,
    storage_path    VARCHAR2(2000) NOT NULL,
    sha256          VARCHAR2(64),
    page_count      NUMBER,
    created_at      TIMESTAMP WITH TIME ZONE DEFAULT SYSTIMESTAMP NOT NULL,

    CONSTRAINT fk_tender_documents_tender
        FOREIGN KEY (tender_id)
        REFERENCES tenders(id)
        ON DELETE CASCADE
);

CREATE TABLE tender_requirements (
    id                  VARCHAR2(36) PRIMARY KEY,
    tender_id           VARCHAR2(36) NOT NULL,
    requirement_code    VARCHAR2(100) NOT NULL,
    title               VARCHAR2(500) NOT NULL,
    description         CLOB,
    weight              NUMBER(6,2) NOT NULL,
    severity            VARCHAR2(30) NOT NULL,
    applicability       VARCHAR2(150),
    is_mandatory        NUMBER(1) DEFAULT 1 NOT NULL,
    active              NUMBER(1) DEFAULT 1 NOT NULL,
    created_at          TIMESTAMP WITH TIME ZONE DEFAULT SYSTIMESTAMP NOT NULL,

    CONSTRAINT fk_tender_req_tender
        FOREIGN KEY (tender_id)
        REFERENCES tenders(id)
        ON DELETE CASCADE,

    CONSTRAINT uq_tender_requirement
        UNIQUE (tender_id, requirement_code),

    CONSTRAINT chk_tender_req_mandatory CHECK (is_mandatory IN (0,1)),
    CONSTRAINT chk_tender_req_active CHECK (active IN (0,1))
);

CREATE TABLE technical_requirements (
    id                      VARCHAR2(36) PRIMARY KEY,
    tender_id               VARCHAR2(36) NOT NULL,
    technical_code          VARCHAR2(100) NOT NULL,
    parameter_name          VARCHAR2(500) NOT NULL,
    minimum_requirement     CLOB NOT NULL,
    classification          VARCHAR2(100),
    comparison_operator     VARCHAR2(50),
    expected_numeric_value  NUMBER,
    expected_text_value     VARCHAR2(1000),
    unit                    VARCHAR2(100),
    created_at              TIMESTAMP WITH TIME ZONE DEFAULT SYSTIMESTAMP NOT NULL,

    CONSTRAINT fk_technical_req_tender
        FOREIGN KEY (tender_id)
        REFERENCES tenders(id)
        ON DELETE CASCADE,

    CONSTRAINT uq_technical_requirement
        UNIQUE (tender_id, technical_code)
);

CREATE TABLE tender_terms (
    id              VARCHAR2(36) PRIMARY KEY,
    tender_id       VARCHAR2(36) NOT NULL,
    term_code       VARCHAR2(100) NOT NULL,
    term_text       CLOB NOT NULL,
    created_at      TIMESTAMP WITH TIME ZONE DEFAULT SYSTIMESTAMP NOT NULL,

    CONSTRAINT fk_tender_terms_tender
        FOREIGN KEY (tender_id)
        REFERENCES tenders(id)
        ON DELETE CASCADE,

    CONSTRAINT uq_tender_term
        UNIQUE (tender_id, term_code)
);

CREATE TABLE bidders (
    id                  VARCHAR2(36) PRIMARY KEY,
    legal_name          VARCHAR2(500) NOT NULL,
    entity_type         VARCHAR2(100),
    registered_address  CLOB,
    pan_reference       VARCHAR2(100),
    gst_reference       VARCHAR2(100),
    udyam_reference     VARCHAR2(150),
    is_synthetic        NUMBER(1) DEFAULT 0 NOT NULL,
    created_at          TIMESTAMP WITH TIME ZONE DEFAULT SYSTIMESTAMP NOT NULL,
    updated_at          TIMESTAMP WITH TIME ZONE DEFAULT SYSTIMESTAMP NOT NULL,

    CONSTRAINT chk_bidders_synthetic CHECK (is_synthetic IN (0,1))
);

CREATE TABLE bid_submissions (
    id                      VARCHAR2(36) PRIMARY KEY,
    tender_id               VARCHAR2(36) NOT NULL,
    bidder_id               VARCHAR2(36) NOT NULL,
    submitted_at            TIMESTAMP WITH TIME ZONE,
    status                  VARCHAR2(50) DEFAULT 'UPLOADED',
    mse_claimed             NUMBER(1) DEFAULT 0 NOT NULL,
    startup_claimed         NUMBER(1) DEFAULT 0 NOT NULL,
    nsic_claimed            NUMBER(1) DEFAULT 0 NOT NULL,
    emd_exemption_claimed   NUMBER(1) DEFAULT 0 NOT NULL,
    offered_make            VARCHAR2(500),
    offered_model           VARCHAR2(500),
    created_at              TIMESTAMP WITH TIME ZONE DEFAULT SYSTIMESTAMP NOT NULL,
    updated_at              TIMESTAMP WITH TIME ZONE DEFAULT SYSTIMESTAMP NOT NULL,

    CONSTRAINT fk_submission_tender
        FOREIGN KEY (tender_id) REFERENCES tenders(id),

    CONSTRAINT fk_submission_bidder
        FOREIGN KEY (bidder_id) REFERENCES bidders(id),

    CONSTRAINT uq_bid_submission UNIQUE (tender_id, bidder_id),

    CONSTRAINT chk_submission_mse CHECK (mse_claimed IN (0,1)),
    CONSTRAINT chk_submission_startup CHECK (startup_claimed IN (0,1)),
    CONSTRAINT chk_submission_nsic CHECK (nsic_claimed IN (0,1)),
    CONSTRAINT chk_submission_emd CHECK (emd_exemption_claimed IN (0,1))
);

CREATE TABLE bidder_documents (
    id                          VARCHAR2(36) PRIMARY KEY,
    submission_id               VARCHAR2(36) NOT NULL,
    document_code               VARCHAR2(100),
    document_type               VARCHAR2(150),
    file_name                   VARCHAR2(1000) NOT NULL,
    storage_path                VARCHAR2(2000) NOT NULL,
    sha256                      VARCHAR2(64),
    page_count                  NUMBER,
    classification_confidence   NUMBER(6,5),
    upload_status               VARCHAR2(50) DEFAULT 'UPLOADED',
    created_at                  TIMESTAMP WITH TIME ZONE DEFAULT SYSTIMESTAMP NOT NULL,

    CONSTRAINT fk_bidder_doc_submission
        FOREIGN KEY (submission_id)
        REFERENCES bid_submissions(id)
        ON DELETE CASCADE
);

CREATE TABLE document_extractions (
    id                  VARCHAR2(36) PRIMARY KEY,
    document_id         VARCHAR2(36) NOT NULL,
    extractor           VARCHAR2(200),
    extractor_version   VARCHAR2(100),
    extracted_text      CLOB,
    fields_json         CLOB,
    tables_json         CLOB,
    raw_response_json   CLOB,
    confidence          NUMBER(6,5),
    created_at          TIMESTAMP WITH TIME ZONE DEFAULT SYSTIMESTAMP NOT NULL,

    CONSTRAINT fk_doc_extract_document
        FOREIGN KEY (document_id)
        REFERENCES bidder_documents(id)
        ON DELETE CASCADE,

    CONSTRAINT chk_doc_extract_fields_json CHECK (fields_json IS JSON),
    CONSTRAINT chk_doc_extract_tables_json CHECK (tables_json IS JSON),
    CONSTRAINT chk_doc_extract_raw_json CHECK (raw_response_json IS JSON)
);

CREATE TABLE verification_sources (
    id              VARCHAR2(36) PRIMARY KEY,
    source_code     VARCHAR2(150) NOT NULL,
    source_name     VARCHAR2(500) NOT NULL,
    source_type     VARCHAR2(100),
    is_synthetic    NUMBER(1) DEFAULT 0 NOT NULL,
    active          NUMBER(1) DEFAULT 1 NOT NULL,
    created_at      TIMESTAMP WITH TIME ZONE DEFAULT SYSTIMESTAMP NOT NULL,

    CONSTRAINT uq_verification_source UNIQUE (source_code),
    CONSTRAINT chk_verification_source_synthetic CHECK (is_synthetic IN (0,1)),
    CONSTRAINT chk_verification_source_active CHECK (active IN (0,1))
);

CREATE TABLE verification_checks (
    id                      VARCHAR2(36) PRIMARY KEY,
    submission_id           VARCHAR2(36) NOT NULL,
    verification_source_id  VARCHAR2(36) NOT NULL,
    requirement_code        VARCHAR2(100),
    request_json            CLOB,
    response_json           CLOB,
    verification_status     VARCHAR2(50),
    checked_at              TIMESTAMP WITH TIME ZONE DEFAULT SYSTIMESTAMP NOT NULL,

    CONSTRAINT fk_verification_submission
        FOREIGN KEY (submission_id)
        REFERENCES bid_submissions(id)
        ON DELETE CASCADE,

    CONSTRAINT fk_verification_source
        FOREIGN KEY (verification_source_id)
        REFERENCES verification_sources(id),

    CONSTRAINT chk_verification_request_json CHECK (request_json IS JSON),
    CONSTRAINT chk_verification_response_json CHECK (response_json IS JSON)
);

CREATE TABLE requirement_results (
    id                      VARCHAR2(36) PRIMARY KEY,
    submission_id           VARCHAR2(36) NOT NULL,
    requirement_id          VARCHAR2(36) NOT NULL,
    status                  VARCHAR2(30) NOT NULL,
    awarded_points          NUMBER(6,2),
    reason                  CLOB,
    ai_explanation          CLOB,
    confidence              NUMBER(6,5),
    requires_human_review   NUMBER(1) DEFAULT 0 NOT NULL,
    evaluated_at            TIMESTAMP WITH TIME ZONE DEFAULT SYSTIMESTAMP NOT NULL,

    CONSTRAINT fk_req_result_submission
        FOREIGN KEY (submission_id)
        REFERENCES bid_submissions(id)
        ON DELETE CASCADE,

    CONSTRAINT fk_req_result_requirement
        FOREIGN KEY (requirement_id)
        REFERENCES tender_requirements(id),

    CONSTRAINT uq_req_result UNIQUE (submission_id, requirement_id),

    CONSTRAINT chk_req_result_status
        CHECK (
            status IN (
                'COMPLIANT',
                'NON_COMPLIANT',
                'MISSING',
                'NEEDS_REVIEW',
                'NOT_APPLICABLE'
            )
        ),

    CONSTRAINT chk_req_result_human
        CHECK (requires_human_review IN (0,1))
);

CREATE TABLE risk_assessments (
    id                  VARCHAR2(36) PRIMARY KEY,
    submission_id       VARCHAR2(36) NOT NULL,
    compliance_score    NUMBER(6,2),
    base_risk           VARCHAR2(30),
    final_risk          VARCHAR2(30),
    calculated_at       TIMESTAMP WITH TIME ZONE DEFAULT SYSTIMESTAMP NOT NULL,

    CONSTRAINT fk_risk_submission
        FOREIGN KEY (submission_id)
        REFERENCES bid_submissions(id)
        ON DELETE CASCADE,

    CONSTRAINT uq_risk_submission UNIQUE (submission_id),

    CONSTRAINT chk_base_risk
        CHECK (base_risk IN ('LOW','MEDIUM','HIGH','CRITICAL')),

    CONSTRAINT chk_final_risk
        CHECK (final_risk IN ('LOW','MEDIUM','HIGH','CRITICAL'))
);

CREATE TABLE audit_events (
    id              NUMBER GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
    tender_id       VARCHAR2(36),
    submission_id   VARCHAR2(36),
    actor_type      VARCHAR2(50),
    actor_id        VARCHAR2(36),
    event_type      VARCHAR2(150) NOT NULL,
    entity_type     VARCHAR2(100),
    entity_id       VARCHAR2(36),
    details_json    CLOB,
    created_at      TIMESTAMP WITH TIME ZONE DEFAULT SYSTIMESTAMP NOT NULL,

    CONSTRAINT fk_audit_tender
        FOREIGN KEY (tender_id)
        REFERENCES tenders(id),

    CONSTRAINT fk_audit_submission
        FOREIGN KEY (submission_id)
        REFERENCES bid_submissions(id),

    CONSTRAINT chk_audit_details_json CHECK (details_json IS JSON)
);

CREATE INDEX idx_tender_req_tender
ON tender_requirements(tender_id);

CREATE INDEX idx_tech_req_tender
ON technical_requirements(tender_id);

CREATE INDEX idx_submission_tender
ON bid_submissions(tender_id);

CREATE INDEX idx_submission_bidder
ON bid_submissions(bidder_id);

CREATE INDEX idx_bidder_docs_submission
ON bidder_documents(submission_id);

CREATE INDEX idx_extractions_document
ON document_extractions(document_id);

CREATE INDEX idx_verification_submission
ON verification_checks(submission_id);

CREATE INDEX idx_req_results_submission
ON requirement_results(submission_id);

CREATE INDEX idx_audit_submission
ON audit_events(submission_id);

CREATE INDEX idx_audit_event_type
ON audit_events(event_type);

COMMIT;

