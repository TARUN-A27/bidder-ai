/* ============================================================
   COMPARISON.JS — sortable + filterable bidder comparison table
   ============================================================ */
document.addEventListener('DOMContentLoaded', () => {
  const tbody = document.querySelector('#comparisonTable tbody');
  const rows = Array.from(tbody.querySelectorAll('tr'));
  const sortButtons = document.querySelectorAll('[data-sort]');
  const search = document.getElementById('bidderSearch');
  const riskFilter = document.getElementById('riskFilter');

  let sortState = { key: 'score', dir: -1 };

  function sortRows() {
    const sorted = [...rows].sort((a, b) => {
      const key = sortState.key;
      let av = a.dataset[key];
      let bv = b.dataset[key];
      if (key === 'score') { av = Number(av); bv = Number(bv); }
      if (av < bv) return -1 * sortState.dir;
      if (av > bv) return 1 * sortState.dir;
      return 0;
    });
    sorted.forEach((row) => tbody.appendChild(row));
  }

  sortButtons.forEach((btn) => {
    btn.addEventListener('click', () => {
      const key = btn.dataset.sort;
      sortState.dir = sortState.key === key ? sortState.dir * -1 : -1;
      sortState.key = key;
      sortRows();
    });
  });

  function applyFilters() {
    const term = (search.value || '').toLowerCase();
    const risk = riskFilter.value;
    rows.forEach((row) => {
      const matchesTerm = row.dataset.name.toLowerCase().includes(term);
      const matchesRisk = !risk || row.dataset.risk === risk;
      row.style.display = matchesTerm && matchesRisk ? '' : 'none';
    });
  }

  search.addEventListener('input', applyFilters);
  riskFilter.addEventListener('change', applyFilters);

  sortRows();
});
