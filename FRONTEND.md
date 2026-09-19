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

The backend does not need CORS for local development. From this checkout, start the two processes in separate terminals:

```bash
cd /home/tarun/TARUN/projects/SIH-PROTO/bidguard-ai/bidguard-ai/backend
PYTHONPATH=. ../../.venv/bin/python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

```bash
cd /home/tarun/TARUN/projects/SIH-PROTO/bidguard-ai/bidguard-ai
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

## AI Performance Insight

The repository currently has no secure server-side generative-AI provider or bidder-performance endpoint. The insight drawer therefore reports an honest provider-unavailable state by default; it does not relabel the synthetic history as AI output and never exposes a browser-side provider key.

The frontend has a ready integration boundary for a future server-side advisory endpoint. A host page may set `window.BIDGUARD_AI_PERFORMANCE_PATH`, or a developer may set `localStorage['bidguard.aiPerformancePath']`, to an API path handled by the existing same-origin API layer. The frontend sends the selected bidder's synthetic historical metrics plus an explicit advisory-only context and expects a response containing `summary`, optional `strengths`, optional `concerns`, optional `performance_outlook`, optional `confidence`, optional `officer_note`, and `advisory: true`. If the endpoint is absent or fails, the UI remains honest and offers retry without fabricating analysis.

Any real provider must remain server-side. AI performance insight never changes compliance, requirement points, assessment score, base/final risk, overrides, comparison order, or the Procurement Officer's final decision.

## Deliberate limitations

- Authentication remains a visual prototype.
- The frozen API exposes no document-content endpoint, so the investigation shows only evidence and verification information returned by requirement results.
- The officer decision page creates a local, explicitly non-persisted draft because the frozen contract exposes no decision or audit endpoint.
- Previous Performance is mapped to the three named synthetic demo bidders in the browser and is not an authoritative registry lookup.
- The dependency-free development proxy buffers uploads; it is intended for the SIH demo rather than production-scale packages.
