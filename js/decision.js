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
  let pendingDecision = '';

  document.getElementById('tenderLink').href = page('tender-detail.html', { tender_id: tenderId });
  document.getElementById('comparisonLink').href = page('comparison.html', { tender_id: tenderId });
  remarks.addEventListener('input', () => { count.textContent = String(remarks.value.length); });

  function closeModal() {
    modal.classList.remove('open');
    modal.setAttribute('aria-hidden', 'true');
  }

  document.querySelector('[data-close-modal]').addEventListener('click', closeModal);
  modal.addEventListener('click', (event) => { if (event.target === modal) closeModal(); });
  document.querySelectorAll('[data-decision]').forEach((button) => button.addEventListener('click', () => {
    if (!remarks.value.trim()) {
      result.classList.add('show');
      result.querySelector('#resultText').textContent = 'Add an officer remark before creating a local draft.';
      result.querySelector('#resultStamp').replaceChildren();
      remarks.focus();
      return;
    }
    pendingDecision = button.dataset.decision;
    document.getElementById('modalTitle').textContent = `Prepare ${pendingDecision.toLowerCase()} draft?`;
    modal.classList.add('open');
    modal.setAttribute('aria-hidden', 'false');
    confirm.focus();
  }));
  confirm.addEventListener('click', () => {
    closeModal();
    result.querySelector('#resultStamp').replaceChildren(window.BidGuardUI.el('span', { className: 'stamp stamp-review stamp-lg', text: `${pendingDecision} · local draft` }));
    result.querySelector('#resultText').textContent = 'Draft prepared for this browser session. It has not been persisted, submitted, or added to an audit trail.';
    result.classList.add('show');
  });

  if (submissionId) {
    try {
      const [submission, assessment] = await Promise.all([
        get(`/submissions/${encodeURIComponent(submissionId)}`),
        get(`/submissions/${encodeURIComponent(submissionId)}/assessment`),
      ]);
      document.getElementById('decisionContext').textContent = `BIDDER · ${submission.bidder_name} · ${submission.submission_id}`;
      document.getElementById('assessmentRecommendation').textContent = assessment.recommendation;
      document.getElementById('assessmentRisk').textContent = `${assessment.score} / 100 · ${assessment.final_risk} risk`;
    } catch (error) {
      document.getElementById('assessmentRecommendation').textContent = error.message || 'Unable to load the persisted assessment.';
    }
  }
});
