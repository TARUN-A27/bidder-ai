document.addEventListener('DOMContentLoaded', async () => {
  const { get } = window.BidGuardAPI;
  const { params, page } = window.BidGuardNav;
  const { clear, el, riskBadge } = window.BidGuardUI;
  const tenderId = params().get('tender_id');
  const state = document.getElementById('comparisonState');
  const tbody = document.querySelector('#comparisonTable tbody');
  const search = document.getElementById('bidderSearch');
  const riskFilter = document.getElementById('riskFilter');
  let bidders = [];

  if (!tenderId) {
    state.className = 'api-state error';
    state.textContent = 'Missing tender_id. Select a tender from the dashboard.';
    return;
  }
  document.getElementById('tenderLink').href = page('tender-detail.html', { tender_id: tenderId });

  function performanceKey(name) {
    if (/Averonix/i.test(name)) return 'A';
    if (/Meralune/i.test(name)) return 'B';
    if (/Kryvanta/i.test(name)) return 'C';
    return '';
  }

  function render() {
    const term = search.value.trim().toLowerCase();
    const risk = riskFilter.value;
    const visible = bidders.filter((bidder) => bidder.bidder_name.toLowerCase().includes(term) && (!risk || bidder.final_risk === risk));
    clear(tbody);
    visible.forEach((bidder) => {
      const issues = Number(bidder.non_compliant_count) + Number(bidder.missing_count) + Number(bidder.needs_review_count);
      const performanceKeyValue = performanceKey(bidder.bidder_name);
      const pp = el('button', { type: 'button', className: 'pp-table-btn', text: 'Previous Performance', dataset: { ppOpen: '', ppBidder: performanceKeyValue, ppName: bidder.bidder_name } });
      const insight = el('button', { type: 'button', className: 'pp-table-btn', text: 'AI Performance Insight', dataset: { aiInsightOpen: '', ppBidder: performanceKeyValue, ppName: bidder.bidder_name } });
      const findings = `${bidder.non_compliant_count} non-compliant · ${bidder.missing_count} missing · ${bidder.needs_review_count} review`;
      tbody.append(el('tr', {}, [
        el('td', {}, [el('strong', { text: bidder.bidder_name }), el('div', { className: 'text-muted', text: bidder.recommendation })]),
        el('td', { className: 'mono', text: bidder.score }),
        el('td', {}, [riskBadge(bidder.final_risk)]),
        el('td', {}, [el('strong', { text: `${issues} total` }), el('div', { className: 'text-muted', text: findings })]),
        el('td', {}, [el('div', { className: 'actions-cell' }, [pp, insight])]),
        el('td', {}, [el('a', { className: 'btn btn-sm', text: 'Investigate', href: page('investigation.html', { submission_id: bidder.submission_id, tender_id: tenderId }) })]),
      ]));
    });
    state.hidden = visible.length > 0;
    state.className = 'api-state';
    state.textContent = bidders.length ? 'No assessed bidders match these filters.' : 'No assessed bidder submissions are available.';
  }

  search.addEventListener('input', render);
  riskFilter.addEventListener('change', render);
  try {
    const comparison = await get(`/tenders/${encodeURIComponent(tenderId)}/comparison`);
    bidders = comparison.bidders || [];
    const counts = { LOW: 0, MEDIUM: 0, HIGH: 0, CRITICAL: 0 };
    bidders.forEach((bidder) => { if (bidder.final_risk in counts) counts[bidder.final_risk] += 1; });
    document.getElementById('totalBidders').textContent = String(bidders.length);
    document.getElementById('countLOW').textContent = String(counts.LOW);
    document.getElementById('countCRITICAL').textContent = String(counts.CRITICAL);
    document.getElementById('attentionCount').textContent = String(counts.MEDIUM + counts.HIGH);
    document.getElementById('comparisonContext').textContent = `TENDER · ${tenderId} · ASSESSED SUBMISSIONS`;
    render();
  } catch (error) {
    state.className = 'api-state error';
    state.textContent = error.message || 'Unable to load bidder comparison.';
  }
});
