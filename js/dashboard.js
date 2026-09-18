document.addEventListener('DOMContentLoaded', async () => {
  const { get } = window.BidGuardAPI;
  const { page } = window.BidGuardNav;
  const { clear, el, formatDate } = window.BidGuardUI;
  const tbody = document.querySelector('#tenderTable tbody');
  const state = document.getElementById('tenderState');
  const count = document.getElementById('tenderCount');
  const totalSubmissions = document.getElementById('totalSubmissions');
  const backendStatus = document.getElementById('backendStatus');
  const search = document.getElementById('tenderSearch');
  let tenders = [];

  function render() {
    const term = search.value.trim().toLowerCase();
    const visible = tenders.filter((tender) =>
      [tender.tender_id, tender.bid_number, tender.title, tender.buyer, tender.dataset_id]
        .some((value) => String(value || '').toLowerCase().includes(term)));
    clear(tbody);
    visible.forEach((tender) => {
      const href = page('tender-detail.html', { tender_id: tender.tender_id });
      tbody.append(el('tr', {}, [
        el('td', { className: 'mono', text: tender.bid_number || tender.dataset_id || tender.tender_id }),
        el('td', {}, [el('strong', { text: tender.title }), el('div', { className: 'text-muted', text: tender.buyer || '' })]),
        el('td', { text: tender.submission_count ?? 0 }),
        el('td', { className: 'mono', text: formatDate(tender.closing_date) }),
        el('td', { className: 'actions-cell' }, [el('a', { className: 'btn btn-primary btn-sm', text: 'View tender', href })]),
      ]));
    });
    state.hidden = visible.length > 0;
    state.className = 'api-state';
    state.textContent = tenders.length ? 'No tenders match this search.' : 'No tenders are available.';
  }

  search.addEventListener('input', render);
  try {
    tenders = await get('/tenders');
    if (!Array.isArray(tenders)) throw new Error('Unexpected tender response.');
    count.textContent = String(tenders.length);
    totalSubmissions.textContent = String(tenders.reduce((sum, tender) => sum + Number(tender.submission_count || 0), 0));
    document.getElementById('availableBadge').textContent = `${tenders.length} available`;
    const now = Date.now();
    const closings = tenders.map((tender) => new Date(tender.closing_date)).filter((date) => !Number.isNaN(date.getTime()) && date.getTime() >= now).sort((a, b) => a - b);
    document.getElementById('nearestClose').textContent = closings.length
      ? closings[0].toLocaleDateString(undefined, { day: '2-digit', month: 'short' })
      : '—';
    backendStatus.className = 'stamp stamp-verified stamp-sm';
    backendStatus.textContent = 'Live backend data';
    render();
  } catch (error) {
    clear(tbody);
    state.hidden = false;
    state.className = 'api-state error';
    state.textContent = error.message || 'Unable to load tenders.';
    backendStatus.className = 'stamp stamp-discrepancy stamp-sm';
    backendStatus.textContent = 'Backend unavailable';
  }
});
