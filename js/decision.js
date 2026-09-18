/* ============================================================
   DECISION.JS
   ============================================================ */
document.addEventListener('DOMContentLoaded', () => {
  const remarks = document.getElementById('remarks');
  const charCount = document.getElementById('charCount');
  const decisionButtons = document.querySelectorAll('[data-decision]');
  const modal = document.getElementById('confirmModal');
  const modalTitle = document.getElementById('modalTitle');
  const modalBody = document.getElementById('modalBody');
  const confirmBtn = document.getElementById('confirmBtn');
  const decisionResult = document.getElementById('decisionResult');
  const resultStamp = document.getElementById('resultStamp');
  const resultText = document.getElementById('resultText');

  remarks.addEventListener('input', () => {
    charCount.textContent = remarks.value.length;
  });

  const copy = {
    APPROVED: {
      title: 'Confirm approval',
      body: 'This will mark XYZ Enterprises as APPROVED for this tender and permanently log the decision with your remarks.',
      stamp: '<span class="stamp stamp-approved stamp-lg">Approved</span>',
      text: 'Decision recorded: <strong>APPROVED</strong>. This action has been added to the audit trail with your remarks.',
    },
    REVIEW: {
      title: 'Confirm send for review',
      body: 'This will flag XYZ Enterprises for further review and notify the auditor queue, along with your remarks.',
      stamp: '<span class="stamp stamp-review stamp-lg">Sent for review</span>',
      text: 'Decision recorded: <strong>SENT FOR REVIEW</strong>. An auditor will follow up on the flagged discrepancies.',
    },
    REJECTED: {
      title: 'Confirm rejection',
      body: 'This will mark XYZ Enterprises as REJECTED for this tender. This action is permanent and will be logged with your remarks.',
      stamp: '<span class="stamp stamp-rejected stamp-lg">Rejected</span>',
      text: 'Decision recorded: <strong>REJECTED</strong>. This action has been added to the audit trail with your remarks.',
    },
  };

  let pendingDecision = null;

  decisionButtons.forEach((btn) => {
    btn.addEventListener('click', () => {
      if (!remarks.value.trim()) {
        showToast('Please add an officer remark before recording a decision.');
        remarks.focus();
        return;
      }
      pendingDecision = btn.dataset.decision;
      const c = copy[pendingDecision];
      modalTitle.textContent = c.title;
      modalBody.textContent = c.body;
      modal.classList.add('open');
    });
  });

  modal.querySelectorAll('[data-close-modal]').forEach((el) => {
    el.addEventListener('click', () => modal.classList.remove('open'));
  });
  modal.addEventListener('click', (e) => { if (e.target === modal) modal.classList.remove('open'); });

  confirmBtn.addEventListener('click', () => {
    if (!pendingDecision) return;
    const c = copy[pendingDecision];
    resultStamp.innerHTML = c.stamp;
    resultText.innerHTML = c.text;
    decisionResult.classList.add('show');
    modal.classList.remove('open');
    decisionResult.scrollIntoView({ behavior: 'smooth', block: 'center' });
    showToast('Decision saved to audit trail.');
  });
});
