document.addEventListener('DOMContentLoaded', async () => {
  const remarks = document.getElementById('remarks');
  const count = document.getElementById('charCount');
  const result = document.getElementById('decisionResult');
  const modal = document.getElementById('confirmModal');
  const confirm = document.getElementById('confirmBtn');
  const { get } = window.BidGuardAPI;
  const { params, page } = window.BidGuardNav;
  const query = params();
  const submissionId = query.get('submission_id');
  const tenderId = query.get('tender_id');
  const decisionButtons = Array.from(document.querySelectorAll('[data-decision]'));
  let pendingDecision = '';
  let modalOpener = null;

  decisionButtons.forEach((button) => { button.disabled = true; });

  document.getElementById('tenderLink').href = page('tender-detail.html', { tender_id: tenderId });
  document.getElementById('comparisonLink').href = page('comparison.html', { tender_id: tenderId });
  remarks.addEventListener('input', () => { count.textContent = String(remarks.value.length); });

  function closeModal() {
    modal.classList.remove('open');
    modal.setAttribute('aria-hidden', 'true');
    Array.from(document.body.children).filter((item) => item !== modal).forEach((item) => { item.inert = false; });
    if (modalOpener) modalOpener.focus();
  }

  document.querySelector('[data-close-modal]').addEventListener('click', closeModal);
  modal.addEventListener('click', (event) => { if (event.target === modal) closeModal(); });
  decisionButtons.forEach((button) => button.addEventListener('click', () => {
    if (!remarks.value.trim()) {
      result.classList.add('show');
      result.querySelector('#resultText').textContent = 'Add an officer remark before creating a local draft.';
      result.querySelector('#resultStamp').replaceChildren();
      remarks.focus();
      return;
    }
    pendingDecision = button.dataset.decision;
    modalOpener = button;
    document.getElementById('modalTitle').textContent = `Prepare ${pendingDecision.toLowerCase()} draft?`;
    modal.classList.add('open');
    modal.setAttribute('aria-hidden', 'false');
    Array.from(document.body.children).filter((item) => item !== modal).forEach((item) => { item.inert = true; });
    confirm.focus();
  }));
  confirm.addEventListener('click', () => {
    closeModal();
    result.querySelector('#resultStamp').replaceChildren(window.BidGuardUI.el('span', { className: 'stamp stamp-review stamp-lg', text: `${pendingDecision} · local draft` }));
    result.querySelector('#resultText').textContent = 'Draft prepared for this browser session. It has not been persisted, submitted, or added to an audit trail.';
    result.classList.add('show');
  });

  document.addEventListener('keydown', (event) => {
    if (!modal.classList.contains('open')) return;
    if (event.key === 'Escape') { closeModal(); return; }
    if (event.key !== 'Tab') return;
    const focusable = Array.from(modal.querySelectorAll('button, [href], input, textarea, select, [tabindex]:not([tabindex="-1"])')).filter((item) => !item.disabled);
    const first = focusable[0]; const last = focusable[focusable.length - 1];
    if (event.shiftKey && document.activeElement === first) { event.preventDefault(); last.focus(); }
    else if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first.focus(); }
  });

  if (submissionId) {
    try {
      const [submission, assessment] = await Promise.all([
        get(`/submissions/${encodeURIComponent(submissionId)}`),
        get(`/submissions/${encodeURIComponent(submissionId)}/assessment`),
      ]);
      document.getElementById('decisionContext').textContent = `BIDDER · ${submission.bidder_name} · ${submission.submission_id}`;
      document.getElementById('assessmentRecommendation').textContent = assessment.recommendation;
      const risk = String(assessment.final_risk || '').toUpperCase();
      const riskStamp = document.getElementById('assessmentRisk');
      riskStamp.textContent = `${assessment.score} / 100 · ${risk} risk`;
      riskStamp.className = `stamp stamp-sm ${risk === 'LOW' ? 'stamp-verified' : risk === 'MEDIUM' ? 'stamp-pending' : risk === 'HIGH' ? 'stamp-high' : 'stamp-discrepancy'}`;
      decisionButtons.forEach((button) => { button.disabled = false; });
    } catch (error) {
      document.getElementById('assessmentRecommendation').textContent = error.message || 'Unable to load the persisted assessment.';
    }
  } else {
    document.getElementById('assessmentRecommendation').textContent = 'Open an assessed bidder from Investigation before preparing an Officer Review Draft.';
  }
});
