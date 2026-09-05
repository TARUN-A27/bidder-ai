# BidGuard AI

Testing prototype for SIH26100: AI-powered bid compliance verification for
GeM procurement.

## Bidder document ingestion

The backend accepts bidder PDFs in either of two forms:

- one ZIP archive;
- multiple multipart files representing a selected folder.

Both endpoints collect a canonical PDF list and call the same
`BidderDocumentIngestionService`. Upload method is not stored in
`BIDDER_DOCUMENTS`, and both paths generate the same method-independent fields:

- deterministic document ID;
- submission ID;
- basename and normalized relative storage path;
- SHA-256;
- PDF page count;
- `UPLOADED` status.

The folder and ZIP must describe the same relative paths to produce identical
rows. A browser folder picker should append each file to `FormData` using
`file.webkitRelativePath || file.name` as the multipart filename.

### Safety rules

- PDF files only, validated by extension, PDF signature, and parser;
- ZIP traversal, absolute paths, Windows paths, backslashes, symlinks,
  encrypted entries, duplicate paths, and non-PDF entries are rejected;
- file-count, individual size, total uncompressed size, archive size, path
  depth, and ZIP compression-ratio limits are enforced;
- extraction happens only inside a submission-specific staging directory;
- database failure removes the newly written submission files;
- a submission with existing documents is rejected instead of duplicated.

## Local setup

```bash
cd backend
python3 -m venv ../.venv
../.venv/bin/python -m pip install -r requirements.txt
cp .env.example .env
```

Set `ORACLE_PASSWORD` in `backend/.env`. Do not commit `.env`.

Start the API:

```bash
cd backend
PYTHONPATH=. ../.venv/bin/python -m uvicorn app.main:app \
  --host 127.0.0.1 --port 8000 --reload
```

Health checks:

```bash
curl http://127.0.0.1:8000/health
curl http://127.0.0.1:8000/health/database
```

### ZIP upload

The submission must already exist in `BID_SUBMISSIONS`.

```bash
curl -X POST \
  http://127.0.0.1:8000/api/v1/submissions/SUBMISSION_UUID/documents/zip \
  -F 'archive=@/absolute/path/Bidder_A.zip;type=application/zip'
```

### Folder upload

Repeat the `files` field and set each multipart filename to its relative path:

```bash
curl -X POST \
  http://127.0.0.1:8000/api/v1/submissions/SUBMISSION_UUID/documents/folder \
  -F 'files=@/absolute/path/gst.pdf;filename=Bidder_A/legal/gst.pdf;type=application/pdf' \
  -F 'files=@/absolute/path/spec.pdf;filename=Bidder_A/technical/spec.pdf;type=application/pdf'
```

## Tests

Unit tests use an in-memory repository and do not need Oracle:

```bash
cd backend
PYTHONPATH=. ../.venv/bin/python -m pytest
```

The suite covers ZIP/folder row equivalence, nested relative paths, PDF
validation, traversal attempts, symlink entries, duplicate paths, repository
inserts, rollback cleanup, and API responses.
