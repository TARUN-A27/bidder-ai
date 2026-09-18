/* ============================================================
   FILE-VIEWER.JS
   Opens a lightweight, styled mock document preview for the
   "Open file" action next to each requirement in the transparent
   compliance score. Frontend-only: generates a placeholder
   preview so the interaction is demonstrable before the backend
   wires up real document storage / retrieval.

   TODO (backend): replace generateMockDocument() + the Blob URL
   below with a real fetch of the stored certificate file (e.g.
   GET /api/bidders/:id/documents/:docId) and open that URL /
   render it in the same tab instead.
   ============================================================ */
(function () {
  function generateMockDocument(label) {
    const now = new Date().toLocaleString('en-IN', { dateStyle: 'medium', timeStyle: 'short' });
    return `<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>${label} — BidGuard AI</title>
<style>
  body{ font-family: 'IBM Plex Sans', Arial, sans-serif; background:#F4F6FC; margin:0; padding:48px 24px; color:#1B1F2B; }
  .sheet{ max-width:720px; margin:0 auto; background:#fff; border-radius:16px; box-shadow:0 12px 28px rgba(27,31,43,.09); overflow:hidden; }
  .head{ padding:26px 32px; background:linear-gradient(135deg,#3452FF,#7C4DFF); color:#fff; }
  .head .seal{ width:38px;height:38px;border-radius:11px;background:rgba(255,255,255,.18);display:flex;align-items:center;justify-content:center;font-family:'IBM Plex Mono',monospace;font-weight:700;margin-bottom:14px; }
  .head h1{ font-size:20px; margin:0 0 4px; }
  .head p{ margin:0; opacity:.85; font-size:13px; }
  .body{ padding:32px; }
  .watermark{ text-align:center; color:#9AA1AF; font-family:'IBM Plex Mono',monospace; font-size:12px; letter-spacing:.08em; text-transform:uppercase; border:1.5px dashed #E2E6F1; border-radius:12px; padding:40px 20px; margin-bottom:24px; }
  .watermark strong{ display:block; font-size:15px; color:#5B6472; margin-bottom:6px; letter-spacing:.02em; }
  .kv{ display:flex; justify-content:space-between; padding:10px 0; border-bottom:1px solid #ECEFF8; font-size:13.5px; }
  .kv span:first-child{ color:#5B6472; }
  .kv span:last-child{ font-family:'IBM Plex Mono',monospace; font-weight:600; }
  .foot{ padding:18px 32px; font-size:11.5px; color:#9AA1AF; font-family:'IBM Plex Mono',monospace; border-top:1px solid #ECEFF8; }
</style>
</head>
<body>
  <div class="sheet">
    <div class="head">
      <div class="seal">BG</div>
      <h1>${label}</h1>
      <p>Document preview · BidGuard AI</p>
    </div>
    <div class="body">
      <div class="watermark">
        <strong>Sample document preview</strong>
        This is a placeholder rendered by the frontend prototype. Connect a real
        document storage endpoint to display the bidder's actual uploaded file here.
      </div>
      <div class="kv"><span>File</span><span>${label}</span></div>
      <div class="kv"><span>Status</span><span>On file</span></div>
      <div class="kv"><span>Opened by</span><span>Procurement Officer</span></div>
      <div class="kv"><span>Opened at</span><span>${now}</span></div>
    </div>
    <div class="foot">BIDGUARD AI · PROTOTYPE PREVIEW · NOT A LEGAL DOCUMENT</div>
  </div>
</body>
</html>`;
  }

  function openCertificateFile(label) {
    const html = generateMockDocument(label);
    const blob = new Blob([html], { type: 'text/html' });
    const url = URL.createObjectURL(blob);
    const win = window.open(url, '_blank');
    if (!win && window.showToast) {
      showToast('Please allow pop-ups to open the document preview.');
    }
  }

  document.addEventListener('click', (e) => {
    const trigger = e.target.closest('[data-open-file]');
    if (!trigger) return;
    openCertificateFile(trigger.dataset.openFile);
  });

  window.openCertificateFile = openCertificateFile;
})();
