document.addEventListener('DOMContentLoaded', async () => {
  const { get } = window.BidGuardAPI;
  const { params, page } = window.BidGuardNav;
  const { clear, el, formatDate, riskBadge } = window.BidGuardUI;
  const query = params();
  const submissionId = query.get('submission_id');
  const tenderIdFromUrl = query.get('tender_id');
  const state = document.getElementById('investigationState');
  const results = document.getElementById('requirementResults');
  const evidenceGrid = document.getElementById('evidenceGrid');
  const scoreBreakdown = document.getElementById('scoreBreakdown');

  if (!submissionId) {
    state.className = 'api-state error';
    state.textContent = 'Missing submission_id. Select an assessed submission from tender detail.';
    return;
  }

  const tabButtons = Array.from(document.querySelectorAll('[data-tab]'));
  function selectTab(button) {
    tabButtons.forEach((item) => {
      const active = item === button;
      item.classList.toggle('active', active);
      item.setAttribute('aria-selected', String(active));
      item.tabIndex = active ? 0 : -1;
    });
    document.querySelectorAll('.tabpanel').forEach((panel) => {
      const active = panel.id === `panel-${button.dataset.tab}`;
      panel.classList.toggle('active', active);
      panel.hidden = !active;
    });
  }
  tabButtons.forEach((button, index) => {
    const panel = document.getElementById(`panel-${button.dataset.tab}`);
    button.id = `tab-${button.dataset.tab}`;
    button.setAttribute('aria-controls', panel.id);
    panel.setAttribute('aria-labelledby', button.id);
    button.tabIndex = index === 0 ? 0 : -1;
    if (index > 0) panel.hidden = true;
    button.addEventListener('click', () => selectTab(button));
    button.addEventListener('keydown', (event) => {
      if (!['ArrowLeft', 'ArrowRight', 'Home', 'End'].includes(event.key)) return;
      event.preventDefault();
      let nextIndex = event.key === 'Home' ? 0 : event.key === 'End' ? tabButtons.length - 1 : index + (event.key === 'ArrowRight' ? 1 : -1);
      nextIndex = (nextIndex + tabButtons.length) % tabButtons.length;
      selectTab(tabButtons[nextIndex]);
      tabButtons[nextIndex].focus();
    });
  });

  const statusClasses = {
    COMPLIANT: 'badge badge-green',
    NEEDS_REVIEW: 'badge badge-amber',
    NON_COMPLIANT: 'badge badge-red',
    MISSING: 'badge badge-red',
    NOT_APPLICABLE: 'badge badge-ink',
  };

  const statusLabels = {
    COMPLIANT: 'Compliant',
    NEEDS_REVIEW: 'Review',
    NON_COMPLIANT: 'Non-compliant',
    MISSING: 'Missing',
    NOT_APPLICABLE: 'N/A',
  };

  function performanceKey(name) {
    if (/Averonix/i.test(name)) return 'A';
    if (/Meralune/i.test(name)) return 'B';
    if (/Kryvanta/i.test(name)) return 'C';
    return '';
  }

  function requirementCard(item) {
    const meta = el('div', { className: 'requirement-meta' }, [
      metaItem('Points', `${item.awarded_points} / ${item.configured_weight}`),
      metaItem('Human review', item.requires_human_review ? 'Required' : 'Not required'),
      metaItem('Sources', (item.source_references || []).join(', ') || 'Not provided', true),
      metaItem('Warnings', (item.warnings || []).join(' ') || 'None', true),
    ]);
    const detail = el('details', { className: 'requirement-detail' }, [
      el('summary', { text: 'Review points, sources and warnings' }),
      meta,
    ]);
    return el('article', { className: `requirement-card status-${item.status}` }, [
      el('div', { className: 'requirement-card-head' }, [
        el('div', {}, [
          el('span', { className: 'requirement-code', text: item.requirement_code }),
          el('h3', { text: item.title }),
        ]),
        el('span', { className: statusClasses[item.status] || 'badge badge-ink', text: statusLabels[item.status] || item.status }),
      ]),
      el('p', { text: item.reason || 'No explanation returned.' }),
      detail,
    ]);
  }

  function metaItem(label, value, full = false) {
    return el('div', { className: `requirement-meta-item${full ? ' full' : ''}` }, [
      el('span', { text: label }),
      el('strong', { text: value }),
    ]);
  }

  function scoreRow(item) {
    const weight = Number(item.configured_weight) || 0;
    const awarded = Number(item.awarded_points) || 0;
    const percent = weight > 0 ? Math.max(0, Math.min(100, (awarded / weight) * 100)) : 0;
    const fill = el('div', { className: 'score-bar-fill' });
    fill.style.width = `${percent}%`;
    if (item.status === 'NEEDS_REVIEW') fill.classList.add('status-review');
    if (item.status === 'NON_COMPLIANT' || item.status === 'MISSING') fill.classList.add('status-fail');
    if (item.status === 'NOT_APPLICABLE') fill.classList.add('status-na');

    return el('div', { className: 'score-bar-row' }, [
      el('div', { className: 'label-wrap' }, [
        el('span', { className: 'label', text: item.title }),
        el('span', { className: 'code', text: item.requirement_code }),
      ]),
      el('div', { className: 'score-bar-track' }, [fill]),
      el('div', { className: 'val', text: `${awarded} / ${weight}` }),
      el('span', { className: `${statusClasses[item.status] || 'badge badge-ink'} score-status`, text: statusLabels[item.status] || item.status }),
    ]);
  }

  function evidenceCard(item) {
    const className = item.status === 'NEEDS_REVIEW' ? 'evidence-card evidence-review' :
      (item.status === 'NON_COMPLIANT' || item.status === 'MISSING' ? 'evidence-card evidence-fail' : 'evidence-card');
    const card = el('article', { className }, [
      el('span', { className: 'tag', text: `${item.requirement_code} · ${statusLabels[item.status] || item.status}` }),
      el('h4', { text: item.title }),
    ]);
    const entries = Object.entries(item.evidence || {});
    if (!entries.length) {
      card.append(el('p', { className: 'text-muted', text: 'No structured evidence returned.' }));
    } else {
      entries.forEach(([key, value]) => card.append(evidenceValue(key, value)));
    }
    card.append(evidenceRow('Sources', (item.source_references || []).join(', ') || 'Not provided'));
    if ((item.warnings || []).length) card.append(evidenceRow('Warnings', item.warnings.join(' ')));
    return card;
  }

  function evidenceValue(key, value, depth = 0) {
    const label = String(key).replaceAll('_', ' ');
    if (value === null || typeof value !== 'object') {
      const display = value === null ? 'Not provided' : typeof value === 'boolean' ? (value ? 'Yes' : 'No') : String(value);
      return evidenceRow(label, display);
    }
    const array = Array.isArray(value);
    const entries = array ? value.map((item, index) => [String(index + 1), item]) : Object.entries(value);
    const details = el('details', { className: 'evidence-tree' }, [
      el('summary', {}, [el('span', { text: label }), el('span', { text: `${entries.length} ${array ? 'items' : 'fields'}` })]),
    ]);
    if (depth === 0 && entries.length <= 4) details.open = true;
    const children = el('div', { className: 'evidence-tree-children' });
    if (!entries.length) children.append(el('p', { className: 'text-muted', text: array ? 'Empty list' : 'Empty object' }));
    entries.forEach(([childKey, childValue]) => children.append(evidenceValue(childKey, childValue, depth + 1)));
    details.append(children);
    return details;
  }

  function evidenceRow(label, value) {
    return el('div', { className: 'evidence-row' }, [
      el('span', { className: 'k', text: label }),
      el('span', { className: 'v', text: value }),
    ]);
  }

  try {
    const [submission, assessment, requirementResults] = await Promise.all([
      get(`/submissions/${encodeURIComponent(submissionId)}`),
      get(`/submissions/${encodeURIComponent(submissionId)}/assessment`),
      get(`/submissions/${encodeURIComponent(submissionId)}/requirement-results`),
    ]);

    const tenderId = assessment.tender_id || tenderIdFromUrl;
    const risk = String(assessment.final_risk || '').toUpperCase();
    const compliant = requirementResults.filter((item) => item.status === 'COMPLIANT').length;
    const attention = requirementResults.filter((item) => ['NEEDS_REVIEW', 'NON_COMPLIANT', 'MISSING'].includes(item.status)).length;
    const humanReview = requirementResults.filter((item) => item.requires_human_review).length;

    document.getElementById('bidderName').textContent = submission.bidder_name;
    document.getElementById('submissionCode').textContent = `TENDER · ${tenderId} · SUBMISSION ${submission.submission_id}`;
    document.getElementById('bidderMeta').textContent = `PAN: ${submission.pan_reference || 'Not provided'} · Submission ${submission.submission_id}`;
    document.getElementById('score').textContent = String(assessment.score);

    const riskStamp = document.getElementById('riskStamp');
    riskStamp.textContent = risk || 'Pending';
    riskStamp.className = `stamp ${risk === 'LOW' ? 'stamp-verified' : risk === 'MEDIUM' ? 'stamp-pending' : 'stamp-discrepancy'}`;

    const scoreRing = document.getElementById('scoreRing');
    scoreRing.classList.add(`risk-${(risk || 'pending').toLowerCase()}`);

    document.getElementById('baseRisk').replaceChildren(riskBadge(assessment.base_risk));
    document.getElementById('finalRisk').replaceChildren(riskBadge(assessment.final_risk));
    document.getElementById('recommendation').textContent = assessment.recommendation;
    document.getElementById('assessedAt').textContent = formatDate(assessment.assessed_at);
    document.getElementById('authority').textContent = assessment.final_decision_authority;
    document.getElementById('resultCount').textContent = `${requirementResults.length} results`;
    document.getElementById('metricTotal').textContent = String(requirementResults.length);
    document.getElementById('metricCompliant').textContent = String(compliant);
    document.getElementById('metricAttention').textContent = String(attention);
    document.getElementById('metricHumanReview').textContent = String(humanReview);

    const statusOverview = document.getElementById('statusOverview');
    clear(statusOverview);
    ['COMPLIANT', 'NEEDS_REVIEW', 'NON_COMPLIANT', 'MISSING', 'NOT_APPLICABLE'].forEach((status) => {
      const value = requirementResults.filter((item) => item.status === status).length;
      statusOverview.append(el('div', { className: 'status-summary' }, [
        el('span', { className: statusClasses[status], text: statusLabels[status] }),
        el('strong', { text: String(value) }),
      ]));
    });

    const overrideList = document.getElementById('overrideList');
    clear(overrideList);
    const overrides = assessment.triggered_risk_overrides || [];
    document.getElementById('overrideExplanation').textContent = overrides.length
      ? `The backend resolved final risk as ${assessment.final_risk} after applying mandatory minimum-risk overrides to base risk ${assessment.base_risk}.`
      : 'No mandatory risk override was triggered; the backend final risk matches its resolved base risk.';
    overrides.forEach((override) => {
      overrideList.append(el('li', {}, [
        el('strong', { text: `${override.override_id} · minimum ${override.minimum_risk}` }),
        el('span', { text: override.reason }),
        el('small', { text: `Related requirements: ${(override.related_requirement_codes || []).join(', ') || 'Not provided'}` }),
      ]));
    });
    if (!overrideList.children.length) overrideList.append(el('li', { text: 'No risk overrides triggered.' }));

    clear(scoreBreakdown);
    clear(results);
    clear(evidenceGrid);
    requirementResults.forEach((item) => {
      scoreBreakdown.append(scoreRow(item));
      results.append(requirementCard(item));
      evidenceGrid.append(evidenceCard(item));
    });
    if (!requirementResults.length) {
      results.append(el('div', { className: 'api-state', text: 'No requirement results were returned.' }));
    }

    document.getElementById('comparisonLink').href = page('comparison.html', { tender_id: tenderId });
    document.getElementById('tenderLink').href = page('tender-detail.html', { tender_id: tenderId });
    const decisionHref = page('decision.html', { submission_id: submissionId, tender_id: tenderId });
    document.getElementById('decisionLink').href = decisionHref;
    document.getElementById('decisionNav').href = decisionHref;

    const ppButton = document.getElementById('previousPerformance');
    ppButton.dataset.ppBidder = performanceKey(submission.bidder_name);
    ppButton.dataset.ppName = submission.bidder_name;
    const insightButton = document.getElementById('aiPerformanceInsight');
    insightButton.dataset.ppBidder = performanceKey(submission.bidder_name);
    insightButton.dataset.ppName = submission.bidder_name;

    state.hidden = true;
  } catch (error) {
    state.className = 'api-state error';
    state.textContent = error.message || 'Unable to load the assessment.';
  }
});
