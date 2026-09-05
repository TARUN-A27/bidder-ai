# BidGuard AI API Contract

Status: **FROZEN FOR FRONTEND INTEGRATION**
Version: **v1 prototype**
Base path: **`/api/v1`**

This contract covers the frontend workflow endpoints currently mounted by FastAPI. Operational routes `/health` and `/health/database` exist outside the base path. The older `/api/v1/submissions/{submission_id}/documents/zip` and `/documents/folder` routes upload PDFs to a pre-created submission; they are not part of the frozen frontend flow. Frontend development should use the tender-scoped import endpoints documented below.

---

## General Rules

- Successful API responses are direct JSON objects or arrays; there is no common success envelope.
- ZIP and multi-file imports use `multipart/form-data`. Other documented endpoints have no request body.
- IDs are opaque strings. Current IDs are UUID-shaped, but the frontend must receive and reuse them rather than construct them.
- Datetimes are JSON strings in ISO 8601 form. Nullable fields are returned as JSON `null`.
- The backend is authoritative for compliance status, points, score, risk, overrides, and recommendation.
- The frontend must display backend-returned assessment values and must not derive bidder decisions.
- Comparison is compliance/risk focused. It is not financial or L1 ranking.
- Recommendations are advisory. The current `final_decision_authority` is `HUMAN_PROCUREMENT_OFFICER`.

Current compliance status values:

- `COMPLIANT`
- `NEEDS_REVIEW`
- `NON_COMPLIANT`
- `MISSING`
- `NOT_APPLICABLE`

Current risk values:

- `LOW`
- `MEDIUM`
- `HIGH`
- `CRITICAL`

## Endpoint Summary

| Method | Path | Purpose | Frontend screen/use |
|---|---|---|---|
| GET | `/api/v1/tenders` | List tenders | Tender dashboard |
| GET | `/api/v1/tenders/{tender_id}` | Get tender requirements and document rules | Tender detail/import preparation |
| GET | `/api/v1/tenders/{tender_id}/submissions` | List bidder submissions | Tender bidder list |
| GET | `/api/v1/submissions/{submission_id}` | Get one submission | Submission header/status |
| POST | `/api/v1/tenders/{tender_id}/submissions/import-zip` | Import a bidder ZIP | ZIP import flow |
| POST | `/api/v1/tenders/{tender_id}/submissions/import-files` | Import multiple bidder PDFs | Folder/multi-file import flow |
| POST | `/api/v1/submissions/{submission_id}/assess` | Run and persist assessment | Explicit assess action |
| GET | `/api/v1/submissions/{submission_id}/assessment` | Read persisted assessment | Assessment summary/detail |
| GET | `/api/v1/submissions/{submission_id}/requirement-results` | Read persisted requirement results | Compliance detail |
| GET | `/api/v1/tenders/{tender_id}/comparison` | Compare assessed submissions | Bidder comparison |

## Endpoints

### GET `/api/v1/tenders`

Purpose: List available tenders.

Request:

- No path or query parameters.
- No body.

Response: HTTP 200, array of tender summaries.

```json
[
  {
    "tender_id": "fccce0a4-ac6b-59b1-8dd9-34061d591384",
    "dataset_id": "SIH26100-T01",
    "bid_number": "GEM/SIH26100-SYNTHETIC/2026/BID-0001",
    "title": "Supply, Installation and Three-Year Onsite Maintenance of High-Speed Document Scanners",
    "buyer": "National Document Digitisation Directorate — Fictional",
    "closing_date": "2026-09-22T15:00:00+05:30",
    "submission_count": 3
  }
]
```

HTTP status codes:

- `200`: tender array returned, including an empty array when no tenders exist.
- `500`: unexpected repository failure; `detail` is `"Assessment operation failed"`.

Frontend notes: Use these fields for tender cards and retain `tender_id` for all tender-scoped calls.

### GET `/api/v1/tenders/{tender_id}`

Purpose: Return one tender plus its active compliance requirements, technical requirements, and required-document definitions.

Request:

- Path: `tender_id` opaque string.
- No query parameters or body.

Response: HTTP 200. The arrays below are shortened to one representative item each; the current seeded tender returns 16 `requirements`, 14 `technical_requirements`, and 22 `mandatory_documents`.

```json
{
  "tender_id": "fccce0a4-ac6b-59b1-8dd9-34061d591384",
  "dataset_id": "SIH26100-T01",
  "bid_number": "GEM/SIH26100-SYNTHETIC/2026/BID-0001",
  "title": "Supply, Installation and Three-Year Onsite Maintenance of High-Speed Document Scanners",
  "buyer": "National Document Digitisation Directorate — Fictional",
  "closing_date": "2026-09-22T15:00:00+05:30",
  "submission_count": 3,
  "requirements": [
    {
      "requirement_code": "DOC-INTEGRITY-001",
      "title": "Document completeness and integrity",
      "description": "Mandatory forms must be signed, legible, internally consistent and free of unresolved material alterations.",
      "weight": 3.0,
      "severity": "MINOR_OR_MAJOR",
      "applicability": "MANDATORY"
    }
  ],
  "technical_requirements": [
    {
      "technical_code": "TECH-001A",
      "parameter_name": "Form factor",
      "minimum_requirement": "A4 sheet-fed duplex document scanner",
      "classification": "Essential"
    }
  ],
  "mandatory_documents": [
    {
      "document_code": "DOC-01",
      "document_name": "Bid cover and tender acceptance",
      "mandatory": true,
      "conditional": false,
      "condition_text": null
    }
  ]
}
```

HTTP status codes:

- `200`: tender returned.
- `404`: unknown tender; string `detail` is `"Tender not found"`.
- `500`: unexpected repository failure.

Frontend notes: Use tender summary fields for the header/card, `requirements` for eligibility context, `technical_requirements` for specifications, and `mandatory_documents` for upload guidance.

### GET `/api/v1/tenders/{tender_id}/submissions`

Purpose: List submissions for one tender, including persisted assessment availability and summary values.

Request:

- Path: `tender_id` opaque string.
- No query parameters or body.

Response: HTTP 200, array of submission objects.

```json
[
  {
    "submission_id": "1c1a2f71-7ae7-5ae8-bdb3-3ef4717c53ad",
    "tender_id": "fccce0a4-ac6b-59b1-8dd9-34061d591384",
    "bidder_id": "95a6ceb0-6f9f-570d-be61-621ce65ac7af",
    "bidder_name": "Averonix Document Systems Private Limited",
    "pan_reference": "SYNTH0001A",
    "dataset_id": "SIH26100-T01",
    "bid_number": "GEM/SIH26100-SYNTHETIC/2026/BID-0001",
    "status": "UPLOADED",
    "offered_model": "ScanSphere NX-4600",
    "mse_claimed": true,
    "startup_claimed": false,
    "nsic_claimed": true,
    "emd_exemption_claimed": true,
    "assessment_available": true,
    "score": 100.0,
    "final_risk": "LOW"
  }
]
```

HTTP status codes:

- `200`: submission array returned.
- `404`: unknown tender.
- `500`: unexpected repository failure.

Frontend notes: Use `assessment_available` to decide whether to enable assessment-detail navigation. `score` and `final_risk` are nullable until an assessment exists.

### GET `/api/v1/submissions/{submission_id}`

Purpose: Return one submission using the same submission object shown above.

Request:

- Path: `submission_id` opaque string.
- No query parameters or body.

Response: HTTP 200.

```json
{
  "submission_id": "1c1a2f71-7ae7-5ae8-bdb3-3ef4717c53ad",
  "tender_id": "fccce0a4-ac6b-59b1-8dd9-34061d591384",
  "bidder_id": "95a6ceb0-6f9f-570d-be61-621ce65ac7af",
  "bidder_name": "Averonix Document Systems Private Limited",
  "pan_reference": "SYNTH0001A",
  "dataset_id": "SIH26100-T01",
  "bid_number": "GEM/SIH26100-SYNTHETIC/2026/BID-0001",
  "status": "UPLOADED",
  "offered_model": "ScanSphere NX-4600",
  "mse_claimed": true,
  "startup_claimed": false,
  "nsic_claimed": true,
  "emd_exemption_claimed": true,
  "assessment_available": true,
  "score": 100.0,
  "final_risk": "LOW"
}
```

HTTP status codes:

- `200`: submission returned.
- `404`: unknown submission; string `detail` is `"Submission not found"`.
- `500`: unexpected repository failure.

Frontend notes: `status` is a nullable stored string, not a frontend-computed state. Ingestion currently creates `UPLOADED`; the assessment service currently accepts `UPLOADED`, `SUBMITTED`, `ASSESSED`, and `COMPLETED` as assessable stored values. The assessment operation does not currently change the stored submission status.

### POST `/api/v1/tenders/{tender_id}/submissions/import-zip`

Purpose: Validate and import a complete bidder ZIP, creating or reusing bidder/submission metadata and storing PDF metadata.

Request:

- Path: `tender_id` opaque string.
- Content type: `multipart/form-data`.
- Required file field: `file` — one `.zip` archive.
- Optional text field: `bidder_metadata` — JSON object string. When omitted, the ZIP must contain `bidder_profile.json`.
- The ZIP may contain PDFs plus `bidder_profile.json` and optionally `document_manifest.json`.

Response: HTTP 201 for a new import or HTTP 200 for an exact reimport. The example shows an exact reimport and abbreviates `documents` to one item.

```json
{
  "submission_id": "1c1a2f71-7ae7-5ae8-bdb3-3ef4717c53ad",
  "bidder_id": "95a6ceb0-6f9f-570d-be61-621ce65ac7af",
  "bidder_name": "Averonix Document Systems Private Limited",
  "tender_id": "fccce0a4-ac6b-59b1-8dd9-34061d591384",
  "document_count": 21,
  "documents": [
    {
      "document_id": "adc0e86e-40ca-528a-a271-ebe8b6a0c8c7",
      "document_code": "DOC-01",
      "document_type": "BID_COVER",
      "filename": "01_Bid_Cover_and_Tender_Acceptance.pdf",
      "normalized_filename": "01_Bid_Cover_and_Tender_Acceptance.pdf",
      "sha256": "62c1fc8b4a749724d5fe16d2bde4b03302869493d222e8139671d35368211a3c",
      "size_bytes": 47832,
      "page_count": 2,
      "processing_status": "UPLOADED"
    }
  ],
  "warnings": [],
  "status": "UPLOADED",
  "ready_for_assessment": true,
  "duplicate_import": true
}
```

HTTP status codes:

- `201`: newly persisted package.
- `200`: exact filename/SHA256 reimport; existing submission returned with `duplicate_import: true`.
- `400`: invalid archive, path, PDF, metadata, or manifest.
- `404`: tender not found.
- `409`: bidder identity conflict, different package for the same tender/bidder, or storage conflict.
- `422`: missing/malformed multipart fields generated by FastAPI validation.
- `503`: database unavailable.
- `500`: unexpected ingestion failure.

Frontend notes: Do not send `mock_portal_data.json`, `expected_result.json`, executables, or nested archives. JSON files other than the two approved metadata names are rejected. Ingestion does not run assessment.

### POST `/api/v1/tenders/{tender_id}/submissions/import-files`

Purpose: Import browser folder/multi-file input through the same package pipeline as ZIP import.

Request:

- Path: `tender_id` opaque string.
- Content type: `multipart/form-data`.
- Required repeated file field: `files` — one or more PDFs.
- Required text field: `bidder_profile` — JSON object string.
- Optional text field: `document_manifest` — JSON object string.

The frontend-oriented flat `bidder_profile` JSON accepts these fields. `bidder_name` and `pan_reference` are required; omitted booleans default to `false`, and unsupported extra fields are rejected.

```json
{
  "dataset_id": "SIH26100-T01",
  "bidder_reference": "BIDDER_A",
  "bidder_name": "Averonix Document Systems Private Limited",
  "entity_type": "PRIVATE_LIMITED_COMPANY",
  "registered_address": "14, Meridian Test Park, Sector S-00, Nayanagar, Test State - 000000, India",
  "pan_reference": "SYNTH0001A",
  "gst_reference": "00SYNTH0001A1ZX",
  "udyam_reference": "UDYAM-ZZ-00-0000001",
  "is_synthetic": true,
  "mse_claimed": true,
  "startup_claimed": false,
  "nsic_claimed": true,
  "emd_exemption_claimed": true,
  "offered_make": "Novacrest",
  "offered_model": "ScanSphere NX-4600"
}
```

The prototype's nested `bidder_profile.json` structure is also accepted. If a manifest is supplied, the backend strictly validates identity, counts, filenames, page counts, and any supplied SHA256 values. Without a manifest, import can succeed with a warning.

Response: Same `SubmissionIngestionResponse` shape and status behavior as ZIP import.

```json
{
  "submission_id": "1c1a2f71-7ae7-5ae8-bdb3-3ef4717c53ad",
  "bidder_id": "95a6ceb0-6f9f-570d-be61-621ce65ac7af",
  "bidder_name": "Averonix Document Systems Private Limited",
  "tender_id": "fccce0a4-ac6b-59b1-8dd9-34061d591384",
  "document_count": 21,
  "documents": [
    {
      "document_id": "adc0e86e-40ca-528a-a271-ebe8b6a0c8c7",
      "document_code": "DOC-01",
      "document_type": "BID_COVER",
      "filename": "01_Bid_Cover_and_Tender_Acceptance.pdf",
      "normalized_filename": "01_Bid_Cover_and_Tender_Acceptance.pdf",
      "sha256": "62c1fc8b4a749724d5fe16d2bde4b03302869493d222e8139671d35368211a3c",
      "size_bytes": 47832,
      "page_count": 2,
      "processing_status": "UPLOADED"
    }
  ],
  "warnings": [],
  "status": "UPLOADED",
  "ready_for_assessment": true,
  "duplicate_import": true
}
```

The `documents` array above is shortened to one representative item; the actual response contains one document object per accepted PDF.

HTTP status codes: `201`, `200`, `400`, `404`, `409`, `422`, `503`, and `500` under the same conditions as ZIP import.

Frontend notes: Browser relative paths may be sent as multipart filenames, but the frozen response exposes safe normalized filenames, not local absolute storage paths.

### POST `/api/v1/submissions/{submission_id}/assess`

Purpose: Explicitly run the existing assessment pipeline and persist the result for a submission.

Request:

- Path: `submission_id` opaque string.
- No query parameters.
- No body.

Response: HTTP 200. The two requirement arrays are shortened to one representative item each; the current tender produces 16 entries in each array.

```json
{
  "score": 100.0,
  "base_risk": "LOW",
  "triggered_risk_overrides": [],
  "final_risk": "LOW",
  "recommendation": "Qualification recommended, subject to Procurement Officer review.",
  "requirement_scores": [
    {
      "requirement_code": "STAT-GST-001",
      "status": "COMPLIANT",
      "configured_weight": 8.0,
      "status_credit": 1.0,
      "applicable": true,
      "awarded_points": 8.0
    }
  ],
  "configured_applicable_weight": 100.0,
  "configured_total_weight": 100.0,
  "final_decision_authority": "HUMAN_PROCUREMENT_OFFICER",
  "submission_id": "1c1a2f71-7ae7-5ae8-bdb3-3ef4717c53ad",
  "bidder_id": "95a6ceb0-6f9f-570d-be61-621ce65ac7af",
  "bidder_name": "Averonix Document Systems Private Limited",
  "tender_id": "fccce0a4-ac6b-59b1-8dd9-34061d591384",
  "assessed_at": "2026-09-05T13:25:27.836983Z",
  "requirement_results": [
    {
      "requirement_code": "STAT-GST-001",
      "status": "COMPLIANT",
      "reason": "Authoritative GST registration is active at bid closing.",
      "requires_human_review": false,
      "evidence": {
        "cancellation_date": null,
        "gstin": "00SYNTH0001A1ZX",
        "status_at_bid_close": "ACTIVE"
      },
      "source_references": ["MOCK_GST_REGISTRY"],
      "warnings": [],
      "title": "Active GST registration",
      "configured_weight": 8.0,
      "awarded_points": 8.0
    }
  ],
  "advisory": true
}
```

When an override triggers, `triggered_risk_overrides` contains objects with these exact fields:

```json
{
  "override_id": "RISK-OVR-005",
  "minimum_risk": "HIGH",
  "reason": "OEM-AUTH-001 is NON_COMPLIANT or MISSING",
  "related_requirement_codes": ["OEM-AUTH-001"]
}
```

HTTP status codes:

- `200`: assessment completed and persisted.
- `404`: submission not found.
- `409`: stored submission state is not assessable.
- `422`: required runtime evidence/configuration is unavailable, invalid, or inconsistent.
- `500`: unexpected assessment failure.

Frontend notes: Assessment is explicit and may take time. Show a loading state, use the returned values directly, and do not calculate statuses, score, risk, overrides, or recommendation in the browser.

### GET `/api/v1/submissions/{submission_id}/assessment`

Purpose: Read only the persisted assessment. This endpoint does not rerun extraction, compliance, or scoring.

Request:

- Path: `submission_id` opaque string.
- No query parameters or body.

Response: HTTP 200 using the exact `AssessmentSummaryResponse` structure shown for POST assess.

```json
{
  "score": 100.0,
  "base_risk": "LOW",
  "triggered_risk_overrides": [],
  "final_risk": "LOW",
  "recommendation": "Qualification recommended, subject to Procurement Officer review.",
  "requirement_scores": [
    {
      "requirement_code": "STAT-GST-001",
      "status": "COMPLIANT",
      "configured_weight": 8.0,
      "status_credit": 1.0,
      "applicable": true,
      "awarded_points": 8.0
    }
  ],
  "configured_applicable_weight": 100.0,
  "configured_total_weight": 100.0,
  "final_decision_authority": "HUMAN_PROCUREMENT_OFFICER",
  "submission_id": "1c1a2f71-7ae7-5ae8-bdb3-3ef4717c53ad",
  "bidder_id": "95a6ceb0-6f9f-570d-be61-621ce65ac7af",
  "bidder_name": "Averonix Document Systems Private Limited",
  "tender_id": "fccce0a4-ac6b-59b1-8dd9-34061d591384",
  "assessed_at": "2026-09-05T13:25:27.836983Z",
  "requirement_results": [
    {
      "requirement_code": "STAT-GST-001",
      "status": "COMPLIANT",
      "reason": "Authoritative GST registration is active at bid closing.",
      "requires_human_review": false,
      "evidence": {
        "cancellation_date": null,
        "gstin": "00SYNTH0001A1ZX",
        "status_at_bid_close": "ACTIVE"
      },
      "source_references": ["MOCK_GST_REGISTRY"],
      "warnings": [],
      "title": "Active GST registration",
      "configured_weight": 8.0,
      "awarded_points": 8.0
    }
  ],
  "advisory": true
}
```

The two arrays above are shortened to one representative item each; the actual persisted arrays contain the same item structures shown under POST assess.

HTTP status codes:

- `200`: persisted assessment returned.
- `404`: submission or persisted assessment not found.
- `500`: unexpected read failure.

Frontend notes: Prefer this GET when refreshing or opening an already assessed submission.

### GET `/api/v1/submissions/{submission_id}/requirement-results`

Purpose: Return only the persisted detailed compliance results.

Request:

- Path: `submission_id` opaque string.
- No query parameters or body.

Response: HTTP 200, array of `PersistedRequirementResult` objects. The current tender returns 16.

```json
[
  {
    "requirement_code": "STAT-GST-001",
    "status": "COMPLIANT",
    "reason": "Authoritative GST registration is active at bid closing.",
    "requires_human_review": false,
    "evidence": {
      "cancellation_date": null,
      "gstin": "00SYNTH0001A1ZX",
      "status_at_bid_close": "ACTIVE"
    },
    "source_references": ["MOCK_GST_REGISTRY"],
    "warnings": [],
    "title": "Active GST registration",
    "configured_weight": 8.0,
    "awarded_points": 8.0
  }
]
```

HTTP status codes:

- `200`: persisted results returned.
- `404`: persisted assessment not found.
- `500`: unexpected read failure.

Frontend notes: Use `status`, `reason`, `requires_human_review`, evidence, references, warnings, and points for the compliance detail view.

### GET `/api/v1/tenders/{tender_id}/comparison`

Purpose: Return compliance/risk summaries for assessed submissions in one tender.

Request:

- Path: `tender_id` opaque string.
- No query parameters or body.

Response: HTTP 200.

```json
{
  "tender_id": "fccce0a4-ac6b-59b1-8dd9-34061d591384",
  "bidders": [
    {
      "submission_id": "1c1a2f71-7ae7-5ae8-bdb3-3ef4717c53ad",
      "bidder_name": "Averonix Document Systems Private Limited",
      "score": 100.0,
      "final_risk": "LOW",
      "recommendation": "Qualification recommended, subject to Procurement Officer review.",
      "non_compliant_count": 0,
      "missing_count": 0,
      "needs_review_count": 0
    },
    {
      "submission_id": "3df0fe49-5742-5416-94f9-72eb220fe32c",
      "bidder_name": "Kryvanta Office Automation Private Limited",
      "score": 34.0,
      "final_risk": "CRITICAL",
      "recommendation": "Strong non-compliance flag; qualification not recommended. Final decision remains with the Procurement Officer.",
      "non_compliant_count": 8,
      "missing_count": 1,
      "needs_review_count": 0
    },
    {
      "submission_id": "f7f2b17d-4739-52f4-aae4-bb26726e6255",
      "bidder_name": "Meralune Imaging Technologies LLP",
      "score": 80.5,
      "final_risk": "HIGH",
      "recommendation": "Not recommended for unconditional qualification. Refer to Procurement Officer for clarification/admissibility review.",
      "non_compliant_count": 2,
      "missing_count": 0,
      "needs_review_count": 2
    }
  ]
}
```

HTTP status codes:

- `200`: comparison returned; `bidders` contains assessed submissions only and may be empty.
- `404`: tender not found.
- `500`: unexpected read failure.

Frontend notes: The current repository orders tender submissions by bidder legal name, and comparison preserves that order. Do not convert this into L1 ranking or infer a final procurement decision.

## Tender Contract

Tender cards may rely on `tender_id`, `dataset_id`, `bid_number`, `title`, `buyer`, `closing_date`, and `submission_count`. Tender detail adds `requirements`, `technical_requirements`, and `mandatory_documents` with the exact nested fields shown above. `dataset_id`, `buyer`, and `closing_date` are nullable.

## Submission Contract

Submission views may rely on `submission_id`, `tender_id`, `bidder_id`, `bidder_name`, `pan_reference`, `dataset_id`, `bid_number`, `status`, `offered_model`, the four claim booleans, `assessment_available`, `score`, and `final_risk`. Nullable fields are `pan_reference`, `dataset_id`, `status`, `offered_model`, `score`, and `final_risk`.

`UPLOADED` is the status created by ingestion and the current persisted A/B/C value. The service also recognizes `SUBMITTED`, `ASSESSED`, and `COMPLETED` as assessable if already stored. This contract does not define a client-side state machine.

## Ingestion Contract

Both import modes feed the same validation and persistence flow and return the same typed response. New imports return `201`; exact reimports return `200` and `duplicate_import: true`; differing packages for an existing tender/bidder return `409`.

The document response fields are `document_id`, nullable `document_code`, `document_type`, `filename`, `normalized_filename`, `sha256`, `size_bytes`, `page_count`, and `processing_status`. Known PDFs receive deterministic classifications. An unknown PDF without a manifest is retained with `document_type: "UNKNOWN"`, `document_code: null`, and a warning. A strict manifest rejects unlisted files.

`ready_for_assessment` reports ingestion readiness only. It does not mean assessment has run. No local absolute storage path is returned.

The frontend must not upload `mock_portal_data.json` or `expected_result.json`. Neither is bidder evidence. Only `bidder_profile.json` and `document_manifest.json` are approved JSON archive metadata.

## Assessment Contract

Assessment starts only through explicit POST assess. Ingestion never auto-assesses. Both POST assess and GET persisted assessment return `AssessmentSummaryResponse`: identifiers, bidder name, score, base/final risk, recommendation, override objects, scoring details, configured weights, decision authority, timestamp, requirement results, and `advisory`.

All values are backend-derived. The frontend should show a pending/loading state during POST, then render the response or refresh it using GET assessment.

## Compliance Requirement Result Contract

Each requirement result contains:

- `requirement_code`: backend requirement identifier.
- `status`: one of the five compliance statuses.
- `reason`: backend explanation.
- `requires_human_review`: explicit review flag.
- `evidence`: requirement-specific JSON object; its internal keys vary by requirement.
- `source_references`: list of backend evidence/source identifiers.
- `warnings`: list of warnings.
- `title`: display title.
- `configured_weight`: configured points available.
- `awarded_points`: points awarded.

Frontend interpretation:

- `COMPLIANT`: requirement satisfied.
- `NEEDS_REVIEW`: Procurement Officer attention is required.
- `NON_COMPLIANT`: requirement failed.
- `MISSING`: required evidence was absent.
- `NOT_APPLICABLE`: requirement excluded from scoring normalization.

## Risk Contract

`base_risk` is the score-derived risk before overrides. `final_risk` is the backend-resolved final risk after any triggered overrides. Each item in `triggered_risk_overrides` contains `override_id`, `minimum_risk`, `reason`, and `related_requirement_codes`.

The frontend must not calculate risk. Display `score`, `base_risk`, `final_risk`, `triggered_risk_overrides`, and `recommendation` exactly as returned. Recommendation remains advisory and `final_decision_authority` remains human.

## Comparison Contract

Comparison returns `tender_id` plus assessed bidders. Each bidder contains `submission_id`, `bidder_name`, `score`, `final_risk`, `recommendation`, `non_compliant_count`, `missing_count`, and `needs_review_count`.

A/B/C can be displayed side by side. The endpoint omits unassessed submissions and does not perform financial/L1 ranking.

## Error Contract

FastAPI always places application errors under top-level `detail`, but the detail shape differs by endpoint family.

Assessment/tender APIs use string detail:

```json
{
  "detail": "Submission not found"
}
```

Tender-scoped ingestion APIs use structured detail:

```json
{
  "detail": {
    "code": "ManifestValidationError",
    "message": "Manifest file set mismatch (missing: example.pdf)"
  }
}
```

FastAPI request validation uses an array:

```json
{
  "detail": [
    {
      "type": "missing",
      "loc": ["body", "file"],
      "msg": "Field required",
      "input": null
    }
  ]
}
```

Status conventions:

- `400`: invalid archive/package, unsafe path, invalid PDF, metadata, or manifest.
- `404`: tender, submission, or persisted assessment not found.
- `409`: invalid assessment state, identity conflict, different package conflict, or storage conflict.
- `422`: FastAPI request validation or assessment evidence/configuration validation.
- `503`: ingestion/database health reports the database unavailable.
- `500`: unexpected internal failure with a sanitized message.

Frontend handling: If `detail` is a string, display it. If it is an object, display `detail.message`. If it is an array, display the first validation `msg` or a generic validation message. Never assume one error-detail shape across all endpoints.

## Frontend Demo Flow

1. `GET /api/v1/tenders`
2. Choose a tender and `GET /api/v1/tenders/{tender_id}` if detail is needed.
3. `GET /api/v1/tenders/{tender_id}/submissions`.
4. Import with tender-scoped ZIP or multi-file POST.
5. Explicitly `POST /api/v1/submissions/{submission_id}/assess`.
6. `GET /api/v1/submissions/{submission_id}/assessment` for persisted display/refresh.
7. `GET /api/v1/submissions/{submission_id}/requirement-results` for the detail view.
8. `GET /api/v1/tenders/{tender_id}/comparison`.

## Frozen Fields

### Frontend may rely on

- Tender: `tender_id`, `dataset_id`, `bid_number`, `title`, `buyer`, `closing_date`, `submission_count`, `requirements`, `technical_requirements`, `mandatory_documents` and their documented nested fields.
- Submission: `submission_id`, `tender_id`, `bidder_id`, `bidder_name`, `pan_reference`, `dataset_id`, `bid_number`, `status`, `offered_model`, claim booleans, `assessment_available`, `score`, `final_risk`.
- Ingestion: all documented submission/document fields, `warnings`, `status`, `ready_for_assessment`, and `duplicate_import`.
- Assessment: identifiers, `score`, `base_risk`, `final_risk`, `recommendation`, `triggered_risk_overrides`, `requirement_scores`, configured weights, `final_decision_authority`, `assessed_at`, `requirement_results`, and `advisory`.
- Requirement results and comparison: every field explicitly documented in their contracts above.

### Frontend must not rely on

- Local filesystem paths or backend storage layout.
- Oracle table names or internal columns not returned by the frozen endpoints.
- Mock verification fixture files.
- `expected_result.json`.
- Undocumented response fields or legacy upload response shapes.
- Frontend-computed compliance statuses, points, score, risk, overrides, recommendation, or final decision.

## Benchmark Demo Expectations

These are QA/demo regression expectations, not client logic:

- Bidder A: `100.0 / LOW`.
- Bidder B: `80.5 / HIGH`.
- Bidder C: `34.0 / CRITICAL`.

**FRONTEND MUST NEVER HARD-CODE THESE RESULTS.** Always display current backend responses.

## API Change Rule

During the hackathon, a backend developer who needs to change an endpoint path, request field, response field, or enum/status value must:

1. Update `docs/API_CONTRACT.md`.
2. Notify the frontend developer.
3. Include the API contract change in the pull request.
4. Get Tech Lead approval before merge.

Breaking contract changes should be avoided after frontend integration begins.
