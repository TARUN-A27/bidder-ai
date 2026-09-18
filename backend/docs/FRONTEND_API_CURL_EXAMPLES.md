# Frontend API curl examples

Base URL: `http://localhost:8000/api/v1`

These examples follow the frozen frontend API contract.

## Important

- Do not construct `tender_id`, `submission_id`, `bidder_id`, or `document_id` in the frontend.
- Use IDs returned by previous backend responses.
- Assessment is explicitly triggered with POST.
- Display backend-returned score, risk, recommendation, compliance status, and points.
- Do not calculate bidder decisions, scores, risk, or rankings in the frontend.

## 1. List tenders

```bash
curl http://localhost:8000/api/v1/tenders
```

Use the returned `tender_id`.

## 2. Get tender details

```bash
curl http://localhost:8000/api/v1/tenders/{tender_id}
```

Replace `{tender_id}` with the ID returned by step 1.

## 3. List submissions

```bash
curl http://localhost:8000/api/v1/tenders/{tender_id}/submissions
```

Use a returned `submission_id` for submission-level operations.

## 4. Get one submission

```bash
curl http://localhost:8000/api/v1/submissions/{submission_id}
```

## 5. Import a ZIP submission

Multipart field: `file`
Optional metadata field: `bidder_metadata`

```bash
curl -X POST -F "file=@submission.zip" http://localhost:8000/api/v1/tenders/{tender_id}/submissions/import-zip
```

For Procurement Officer uploads, bidder identity is derived from bidder evidence. The optional `bidder_metadata` field remains supported only for backward compatibility/testing.

The response returns a `submission_id`. Use that backend-returned ID for assessment.

## 6. Import multiple PDF files

Multipart file field: `files` and repeat it for each PDF.
Metadata field: `bidder_profile`.

```bash
curl -X POST -F "files=@technical.pdf" -F "files=@commercial.pdf" http://localhost:8000/api/v1/tenders/{tender_id}/submissions/import-files
```

### Bulk ZIP containing multiple bidder folders

```bash
curl -X POST -F "file=@tender_submissions.zip" http://localhost:8000/api/v1/tenders/{tender_id}/submissions/import-bulk-zip
```

### Parent folder upload

Repeat `files` and preserve each relative path in the multipart filename.

```bash
curl -X POST \
  -F "files=@A-gst.pdf;filename=bidders/Bidder_A/documents/A-gst.pdf" \
  -F "files=@B-gst.pdf;filename=bidders/Bidder_B/documents/B-gst.pdf" \
  http://localhost:8000/api/v1/tenders/{tender_id}/submissions/import-folder
```

## 7. Explicitly assess a submission

No request body is required.

```bash
curl -X POST http://localhost:8000/api/v1/submissions/{submission_id}/assess
```

The response contains backend-authoritative score, risk, recommendation, requirement scores, requirement results, and final decision authority.

## 8. Get the persisted assessment

```bash
curl http://localhost:8000/api/v1/submissions/{submission_id}/assessment
```

Use this when opening or refreshing an assessment.

## 9. Get requirement results

```bash
curl http://localhost:8000/api/v1/submissions/{submission_id}/requirement-results
```

## 10. Get tender comparison

```bash
curl http://localhost:8000/api/v1/tenders/{tender_id}/comparison
```

The comparison is compliance/risk-focused and is not an L1 financial ranking.

## Recommended frontend sequence

1. GET `/api/v1/tenders`
2. Choose the returned `tender_id`.
3. GET `/api/v1/tenders/{tender_id}/submissions`
4. Import the submission.
5. Use the returned `submission_id`.
6. POST `/api/v1/submissions/{submission_id}/assess`
7. GET `/api/v1/submissions/{submission_id}/assessment`
8. GET `/api/v1/submissions/{submission_id}/requirement-results`
9. GET `/api/v1/tenders/{tender_id}/comparison`

## Error handling

Application errors use a top-level `detail`.

String detail example:

```json
{
  "detail": "Submission not found"
}
```

Structured ingestion error example:

```json
{
  "detail": {
    "code": "ManifestValidationError",
    "message": "Manifest file set mismatch (missing: example.pdf)"
  }
}
```

FastAPI request-validation errors use an array:

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

Frontend handling should support:
1. string `detail`
2. object `detail.message`
3. array `detail[0].msg`

Do not assume every error response has the same shape.
