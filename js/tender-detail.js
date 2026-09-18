document.addEventListener('DOMContentLoaded', async () => {
  const { get } = window.BidGuardAPI;
  const { params, page } = window.BidGuardNav;
  const { clear, el, formatDate, riskBadge } = window.BidGuardUI;
  const tenderId = params().get('tender_id');
  const state = document.getElementById('detailState');
  const requirementList = document.getElementById('requirementList');
  const submissionBody = document.querySelector('#submissionTable tbody');

  if (!tenderId) {
    state.className = 'api-state error';
    state.textContent = 'Missing tender_id. Return to the dashboard and select a tender.';
    return;
  }
  document.getElementById('importLink').href = page('upload-bidder.html', { tender_id: tenderId });
  document.getElementById('secondaryImportLink').href = page('upload-bidder.html', { tender_id: tenderId });
  document.getElementById('comparisonLink').href = page('comparison.html', { tender_id: tenderId });

  function renderRequirements(tender) {
    clear(requirementList);
    tender.requirements.forEach((requirement) => requirementList.append(el('div', { className: 'req-item' }, [
      el('div', { className: 'check', text: '✓' }),
      el('div', { className: 'name' }, [el('strong', { text: requirement.title }), el('div', { className: 'text-muted', text: requirement.description })]),
      el('span', { className: 'tag', text: requirement.applicability }),
    ])));
    document.getElementById('requirementCount').textContent = `${tender.requirements.length} requirements`;
  }

  function renderSubmissions(submissions) {
    clear(submissionBody);
    submissions.forEach((submission) => {
      const action = submission.assessment_available
        ? el('a', { className: 'btn btn-sm', text: 'View assessment', href: page('investigation.html', { submission_id: submission.submission_id, tender_id: tenderId, bidder_id: submission.bidder_id }) })
        : el('a', { className: 'btn btn-primary btn-sm', text: 'Run assessment', href: page('processing.html', { submission_id: submission.submission_id, tender_id: tenderId, bidder_id: submission.bidder_id }) });
      submissionBody.append(el('tr', {}, [
        el('td', {}, [el('strong', { text: submission.bidder_name }), el('div', { className: 'text-muted mono', text: submission.pan_reference || '' })]),
        el('td', { className: 'mono', text: submission.score == null ? '—' : submission.score }),
        el('td', {}, [riskBadge(submission.final_risk)]),
        el('td', { text: submission.status || 'Not provided' }),
        el('td', { className: 'actions-cell' }, [action]),
      ]));
    });
    document.getElementById('submissionCount').textContent = `${submissions.length} submitted`;
    document.getElementById('submissionEmpty').hidden = submissions.length > 0;
  }

  try {
    const [tender, submissions] = await Promise.all([
      get(`/tenders/${encodeURIComponent(tenderId)}`),
      get(`/tenders/${encodeURIComponent(tenderId)}/submissions`),
    ]);
    document.getElementById('tenderCode').textContent = tender.bid_number || tender.dataset_id || tender.tender_id;
    document.getElementById('tenderTitle').textContent = tender.title;
    document.getElementById('buyer').textContent = tender.buyer || 'Not provided';
    document.getElementById('closingDate').textContent = formatDate(tender.closing_date);
    document.getElementById('datasetId').textContent = tender.dataset_id || tender.tender_id;
    document.getElementById('bidNumber').textContent = tender.bid_number || 'Not provided';
    document.getElementById('ruleSet').textContent = `${tender.requirements.length} trusted requirements`;
    renderRequirements(tender);
    renderSubmissions(submissions);
    state.hidden = true;
  } catch (error) {
    state.className = 'api-state error';
    state.textContent = error.message || 'Unable to load tender details.';
  }
});
