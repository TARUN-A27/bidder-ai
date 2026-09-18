document.addEventListener('DOMContentLoaded', async () => {
  const { get, post } = window.BidGuardAPI;
  const { params, page } = window.BidGuardNav;
  const { clear, el, riskBadge } = window.BidGuardUI;
  const query = params();
  const submissionId = query.get('submission_id');
  const tenderId = query.get('tender_id');
  const bidderId = query.get('bidder_id');
  const button = document.getElementById('assessButton');
  const state = document.getElementById('assessmentState');
  const result = document.getElementById('assessmentResult');
  const doneActions = document.getElementById('doneActions');
  const rows = Array.from(document.querySelectorAll('.pipe-row'));

  document.getElementById('backLink').href = page('tender-detail.html', { tender_id: tenderId });
  document.getElementById('comparisonNav').href = page('comparison.html', { tender_id: tenderId });
  if (!submissionId) {
    state.className = 'api-state error';
    state.textContent = 'Missing submission_id. Select a submission from tender detail.';
    button.disabled = true;
  }

  if (submissionId) {
    try {
      const submission = await get(`/submissions/${encodeURIComponent(submissionId)}`);
      document.getElementById('submissionContext').textContent = `BIDDER · ${submission.bidder_name} · ${submission.submission_id}`;
    } catch (_) {
      document.getElementById('submissionContext').textContent = `SUBMISSION · ${submissionId}`;
    }
  }

  function field(label, value) {
    return el('div', { className: 'key-row' }, [el('span', { className: 'key', text: label }), typeof value === 'string' ? el('strong', { text: value }) : value]);
  }

  button.addEventListener('click', async () => {
    button.disabled = true;
    document.getElementById('overallStatus').textContent = 'Processing';
    document.getElementById('progressFill').style.width = '35%';
    rows.forEach((row, index) => {
      row.className = `pipe-row${index === 0 ? ' active' : ''}`;
      row.querySelector('.status').textContent = index === 0 ? 'Processing' : 'Backend managed';
    });
    document.getElementById('stepCounter').textContent = 'ASSESSMENT IN PROGRESS';
    document.getElementById('etaLabel').textContent = 'AWAITING BACKEND RESULT';
    state.className = 'api-state';
    state.textContent = 'Assessment processing is in progress. Azure extraction and verification may take several minutes; keep this page open.';
    try {
      const assessment = await post(`/submissions/${encodeURIComponent(submissionId)}/assess`);
      state.className = 'api-state success';
      state.textContent = 'Assessment completed and persisted by the backend.';
      document.getElementById('overallStatus').textContent = 'Complete';
      document.getElementById('progressFill').style.width = '100%';
      rows.forEach((row) => { row.className = 'pipe-row done'; row.querySelector('.dot').textContent = '✓'; row.querySelector('.status').textContent = 'Complete'; });
      document.getElementById('stepCounter').textContent = '6 / 6 COMPLETE';
      document.getElementById('etaLabel').textContent = 'PERSISTED BY BACKEND';
      clear(result);
      const overrides = assessment.triggered_risk_overrides || [];
      result.append(el('div', { className: 'key-list' }, [
        field('Bidder', assessment.bidder_name),
        field('Score', String(assessment.score)),
        field('Base risk', riskBadge(assessment.base_risk)),
        field('Final risk', riskBadge(assessment.final_risk)),
        field('Recommendation', assessment.recommendation),
        field('Risk overrides', overrides.length ? overrides.map((item) => item.override_id).join(', ') : 'None'),
        field('Decision authority', assessment.final_decision_authority),
      ]));
      result.append(el('div', { className: 'flex-gap mt-24' }, [
        el('a', { className: 'btn btn-primary', text: 'View Assessment', href: page('investigation.html', { submission_id: assessment.submission_id, tender_id: assessment.tender_id, bidder_id: assessment.bidder_id }) }),
        el('a', { className: 'btn', text: 'Bidder Comparison', href: page('comparison.html', { tender_id: assessment.tender_id }) }),
      ]));
      doneActions.hidden = false;
    } catch (error) {
      state.className = 'api-state error';
      state.textContent = error.message || 'Assessment failed.';
      button.disabled = false;
      button.textContent = 'Retry Assessment';
      document.getElementById('overallStatus').textContent = 'Failed';
      document.getElementById('progressFill').style.width = '0';
      rows.forEach((row) => { row.className = 'pipe-row'; row.querySelector('.status').textContent = 'Not confirmed'; });
      document.getElementById('stepCounter').textContent = 'ASSESSMENT FAILED';
      document.getElementById('etaLabel').textContent = 'REVIEW ERROR AND RETRY';
    }
  });
});
