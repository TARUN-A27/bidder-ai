# BidGuard AI frontend

The hackathon frontend intentionally remains static HTML, CSS, and JavaScript. It now uses the frozen backend contract for the operational workflow:

1. dashboard loads `GET /api/v1/tenders`;
2. tender detail loads the tender and its submissions;
3. bidder ZIP or PDF packages use the tender-scoped import endpoints;
4. assessment starts only with `POST /api/v1/submissions/{submission_id}/assess`;
5. investigation reads the persisted submission, assessment, and requirement results; and
6. comparison reads the backend comparison without reordering it.

Identifiers are propagated through page query parameters. `js/api.js` is the shared request, backend-error, URL, and safe DOM helper layer. Assessment scores, risks, requirement statuses, evidence, overrides, and recommendations are backend authoritative.

## API base and local development

The API base defaults to same-origin `/api/v1`. A host page may set `window.BIDGUARD_API_BASE` before loading `js/api.js`, or a developer may configure the browser console once:

```js
localStorage.setItem('bidguard.apiBase', 'http://127.0.0.1:8000/api/v1')
```

The backend does not need CORS for local development. Start it on port 8000, then run the dependency-free same-origin frontend host from the repository root:

```bash
python3 scripts/dev_frontend_server.py
```

Open `http://127.0.0.1:5500/dashboard.html`. Static assets and `/api/v1/*` now share the same browser origin; the development host proxies `/api/*` to `http://127.0.0.1:8000/api/*`.

No frontend build is required. For static visual inspection without a backend:

```bash
python3 -m http.server 5500
```

Direct `file://` use cannot reach the default same-origin API path.

## Previous Performance

Previous Performance remains an isolated frontend-only synthetic advisory. Its data is held only in `js/previous-performance.js`; it never modifies assessment score, risk, requirement status, compliance, qualification, or comparison order. The Procurement Officer remains the final decision authority.

## Deliberate limitations

- Authentication remains a visual prototype.
- The frozen API exposes no document-content endpoint, so the investigation shows only evidence and verification information returned by requirement results.
- The officer decision page creates a local, explicitly non-persisted draft because the frozen contract exposes no decision or audit endpoint.
