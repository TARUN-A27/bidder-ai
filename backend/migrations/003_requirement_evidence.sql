SET SQLBLANKLINES ON
WHENEVER SQLERROR EXIT SQL.SQLCODE
WHENEVER OSERROR EXIT FAILURE

CREATE TABLE requirement_evidence_rules (
    id                  VARCHAR2(36) PRIMARY KEY,
    requirement_id      VARCHAR2(36) NOT NULL,
    evidence_text       VARCHAR2(1000) NOT NULL,
    evidence_order      NUMBER NOT NULL,
    mandatory_evidence  NUMBER(1) DEFAULT 1 NOT NULL,
    active              NUMBER(1) DEFAULT 1 NOT NULL,

    CONSTRAINT fk_req_evidence_requirement
        FOREIGN KEY (requirement_id)
        REFERENCES tender_requirements(id)
        ON DELETE CASCADE,

    CONSTRAINT uq_req_evidence
        UNIQUE (requirement_id, evidence_text),

    CONSTRAINT chk_req_evidence_mandatory
        CHECK (mandatory_evidence IN (0,1)),

    CONSTRAINT chk_req_evidence_active
        CHECK (active IN (0,1))
);

CREATE INDEX idx_req_evidence_requirement
ON requirement_evidence_rules(requirement_id);

COMMIT;
