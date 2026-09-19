document.addEventListener('DOMContentLoaded', async () => {
  const { get, post } = window.BidGuardAPI;
  const { params, page } = window.BidGuardNav;
  const { clear, el, riskBadge } = window.BidGuardUI;
  const query = params();
  const submissionId = query.get('submission_id');
  let tenderId = query.get('tender_id');
  const button = document.getElementById('assessButton');
  const state = document.getElementById('assessmentState');
  const workspace = document.getElementById('assessmentWorkspace');
  const result = document.getElementById('assessmentResult');
  const doneActions = document.getElementById('doneActions');
  const rows = Array.from(document.querySelectorAll('.pipe-row'));
  const progressTrack = document.getElementById('progressTrack');

  function updateLinks() {
    document.getElementById('backLink').href = page('tender-detail.html', { tender_id: tenderId });
    document.getElementById('comparisonNav').href = page('comparison.html', { tender_id: tenderId });
  }
  updateLinks();

  function field(label, value) {
    return el('div', { className: 'key-row' }, [el('span', { className: 'key', text: label }), typeof value === 'string' ? el('strong', { text: value }) : value]);
  }

  function markComplete() {
    workspace.setAttribute('aria-busy', 'false');
    document.getElementById('overallStatus').textContent = 'Complete';
    progressTrack.className = 'progress-track mb-24 complete';
    rows.forEach((row, index) => {
      row.className = 'pipe-row done';
      row.querySelector('.dot').textContent = String(index + 1);
      row.querySelector('.status').textContent = 'Confirmed';
    });
    document.getElementById('stepCounter').textContent = 'ASSESSMENT COMPLETE';
    document.getElementById('etaLabel').textContent = 'PERSISTED BY BACKEND';
  }

  function renderAssessment(assessment, message) {
    state.className = 'api-state success';
    state.textContent = message;
    markComplete();
    clear(result);
    const overrides = assessment.triggered_risk_overrides || [];
    result.append(el('div', { className: 'key-list' }, [
      field('Bidder', assessment.bidder_name),
      field('Score', `${assessment.score} / 100`),
      field('Base risk', riskBadge(assessment.base_risk)),
      field('Final risk', riskBadge(assessment.final_risk)),
      field('Recommendation', assessment.recommendation),
      field('Risk overrides', overrides.length ? overrides.map((item) => item.override_id).join(', ') : 'None'),
      field('Decision authority', assessment.final_decision_authority),
    ]));
    result.append(el('div', { className: 'flex-gap mt-24' }, [
      el('a', { className: 'btn btn-primary', text: 'View assessment', href: page('investigation.html', { submission_id: assessment.submission_id, tender_id: assessment.tender_id }) }),
      el('a', { className: 'btn', text: 'Compliance & Risk Comparison', href: page('comparison.html', { tender_id: assessment.tender_id }) }),
    ]));
    doneActions.hidden = false;
    button.hidden = true;
  }

  function markProcessing() {
    workspace.setAttribute('aria-busy', 'true');
    button.disabled = true;
    document.getElementById('overallStatus').textContent = 'Processing';
    progressTrack.className = 'progress-track mb-24 active';
    rows.forEach((row, index) => {
      row.className = `pipe-row${index === 0 ? ' active' : ''}`;
      row.querySelector('.status').textContent = index === 0 ? 'Request active' : 'Backend managed';
    });
    document.getElementById('stepCounter').textContent = 'ASSESSMENT IN PROGRESS';
    document.getElementById('etaLabel').textContent = 'AWAITING AUTHORITATIVE RESULT';
    state.className = 'api-state';
    state.textContent = 'The backend is processing stored bidder PDFs through extraction, verification, compliance, scoring and persistence. Keep this page open.';
  }

  function markFailed(message) {
    workspace.setAttribute('aria-busy', 'false');
    state.className = 'api-state error';
    state.textContent = message;
    button.disabled = false;
    button.textContent = 'Retry assessment';
    document.getElementById('overallStatus').textContent = 'Not confirmed';
    progressTrack.className = 'progress-track mb-24';
    rows.forEach((row) => { row.className = 'pipe-row'; row.querySelector('.status').textContent = 'Not confirmed'; });
    document.getElementById('stepCounter').textContent = 'RESULT NOT CONFIRMED';
    document.getElementById('etaLabel').textContent = 'REVIEW ERROR BEFORE RETRYING';
  }

  if (!submissionId) {
    markFailed('Missing submission_id. Select a submission from tender detail.');
    button.disabled = true;
    return;
  }

  try {
    const submission = await get(`/submissions/${encodeURIComponent(submissionId)}`);
    tenderId = submission.tender_id;
    updateLinks();
    document.getElementById('submissionContext').textContent = `BIDDER · ${submission.bidder_name} · ${submission.submission_id}`;
    if (submission.assessment_available) {
      const persisted = await get(`/submissions/${encodeURIComponent(submissionId)}/assessment`);
      renderAssessment(persisted, 'A persisted assessment already exists. No new assessment request was sent.');
      return;
    }
  } catch (error) {
    markFailed(error.message || 'Unable to validate this submission.');
    button.disabled = true;
    return;
  }

  button.addEventListener('click', async () => {
    markProcessing();
    try {
      const assessment = await post(`/submissions/${encodeURIComponent(submissionId)}/assess`);
      renderAssessment(assessment, 'Assessment completed and persisted by the backend.');
    } catch (error) {
      try {
        const persisted = await get(`/submissions/${encodeURIComponent(submissionId)}/assessment`);
        renderAssessment(persisted, 'The assessment request ended unexpectedly, but a persisted backend result was recovered safely.');
      } catch (_) {
        markFailed(error.message || 'Assessment failed and no persisted result could be recovered.');
      }
    }
  });
});
