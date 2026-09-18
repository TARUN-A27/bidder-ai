document.addEventListener('DOMContentLoaded', async () => {
  const { get } = window.BidGuardAPI;
  const { params, page } = window.BidGuardNav;
  const { clear, el, formatDate, riskBadge } = window.BidGuardUI;
  const tenderId = params().get('tender_id');
  const state = document.getElementById('detailState');
  const requirementList = document.getElementById('requirementList');
  const technicalList = document.getElementById('technicalList');
  const documentList = document.getElementById('documentList');
  const submissionBody = document.querySelector('#submissionTable tbody');

  if (!tenderId) {
    state.className = 'api-state error';
    state.textContent = 'Missing tender_id. Return to the dashboard and select a tender.';
    return;
  }
  document.getElementById('importLink').href = page('upload-bidder.html', { tender_id: tenderId });
  document.getElementById('secondaryImportLink').href = page('upload-bidder.html', { tender_id: tenderId });
  document.getElementById('comparisonLink').href = page('comparison.html', { tender_id: tenderId });

  const tabButtons = Array.from(document.querySelectorAll('[data-tender-tab]'));
  function selectTab(button) {
    tabButtons.forEach((item) => {
      const active = item === button;
      item.classList.toggle('active', active);
      item.setAttribute('aria-selected', String(active));
      item.tabIndex = active ? 0 : -1;
      const panel = document.getElementById(`tender-panel-${item.dataset.tenderTab}`);
      panel.hidden = !active;
      panel.classList.toggle('active', active);
    });
  }
  tabButtons.forEach((button, index) => {
    button.addEventListener('click', () => selectTab(button));
    button.addEventListener('keydown', (event) => {
      if (!['ArrowLeft', 'ArrowRight'].includes(event.key)) return;
      event.preventDefault();
      const offset = event.key === 'ArrowRight' ? 1 : -1;
      const next = tabButtons[(index + offset + tabButtons.length) % tabButtons.length];
      selectTab(next); next.focus();
    });
  });

  function renderRequirements(tender) {
    clear(requirementList);
    tender.requirements.forEach((requirement) => requirementList.append(el('div', { className: 'req-item' }, [
      el('div', { className: 'check', text: '✓' }),
      el('div', { className: 'name' }, [el('strong', { text: requirement.title }), el('div', { className: 'text-muted', text: requirement.description || 'No description provided.' })]),
      el('span', { className: 'tag', text: requirement.applicability || requirement.severity || 'Configured' }),
    ])));
    document.getElementById('requirementCount').textContent = `${tender.requirements.length} requirements`;
    clear(technicalList);
    tender.technical_requirements.forEach((item) => technicalList.append(el('div', { className: 'definition-row' }, [
      el('span', { className: 'definition-code', text: item.technical_code }),
      el('div', {}, [el('strong', { text: item.parameter_name }), el('p', { text: item.minimum_requirement })]),
      el('span', { className: 'badge badge-ink', text: item.classification || 'Configured' }),
    ])));
    clear(documentList);
    tender.mandatory_documents.forEach((item) => documentList.append(el('div', { className: 'definition-row' }, [
      el('span', { className: 'definition-code', text: item.document_code }),
      el('div', {}, [el('strong', { text: item.document_name }), el('p', { text: item.condition_text || (item.mandatory ? 'Required for this tender.' : 'Supporting document.') })]),
      el('span', { className: item.conditional ? 'badge badge-amber' : 'badge badge-ink', text: item.conditional ? 'Conditional' : item.mandatory ? 'Mandatory' : 'Optional' }),
    ])));
    document.getElementById('technicalCount').textContent = `${tender.technical_requirements.length} technical`;
    document.getElementById('documentCount').textContent = `${tender.mandatory_documents.length} documents`;
  }

  function performanceKey(name) {
    if (/Averonix/i.test(name)) return 'A';
    if (/Meralune/i.test(name)) return 'B';
    if (/Kryvanta/i.test(name)) return 'C';
    return '';
  }

  function renderSubmissions(submissions) {
    clear(submissionBody);
    submissions.forEach((submission) => {
      const action = submission.assessment_available
        ? el('a', { className: 'btn btn-sm', text: 'View assessment', href: page('investigation.html', { submission_id: submission.submission_id, tender_id: tenderId, bidder_id: submission.bidder_id }) })
        : el('a', { className: 'btn btn-primary btn-sm', text: 'Run assessment', href: page('processing.html', { submission_id: submission.submission_id, tender_id: tenderId, bidder_id: submission.bidder_id }) });
      const history = el('button', { type: 'button', className: 'pp-table-btn', text: 'Previous Performance', dataset: { ppOpen: '', ppBidder: performanceKey(submission.bidder_name), ppName: submission.bidder_name } });
      const insight = el('button', { type: 'button', className: 'pp-table-btn', text: 'AI Performance Insight', dataset: { aiInsightOpen: '', ppBidder: performanceKey(submission.bidder_name), ppName: submission.bidder_name } });
      submissionBody.append(el('tr', {}, [
        el('td', {}, [el('strong', { text: submission.bidder_name }), el('div', { className: 'text-muted mono', text: submission.pan_reference || '' })]),
        el('td', { text: submission.offered_model || 'Not provided' }),
        el('td', { className: 'mono', text: submission.score == null ? '—' : submission.score }),
        el('td', {}, [riskBadge(submission.final_risk)]),
        el('td', { text: submission.status || 'Not provided' }),
        el('td', { className: 'actions-cell' }, [action, history, insight]),
      ]));
    });
    document.getElementById('submissionCount').textContent = `${submissions.length} submitted`;
    document.getElementById('submissionEmpty').hidden = submissions.length > 0;
    document.getElementById('submissionSummary').textContent = String(submissions.length);
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
    renderRequirements(tender);
    renderSubmissions(submissions);
    state.hidden = true;
  } catch (error) {
    state.className = 'api-state error';
    state.textContent = error.message || 'Unable to load tender details.';
  }
});
