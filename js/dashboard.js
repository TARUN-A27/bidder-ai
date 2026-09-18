/* ============================================================
   DASHBOARD.JS — client-side search & status filter
   ============================================================ */
document.addEventListener('DOMContentLoaded', () => {
  const search = document.getElementById('tenderSearch');
  const statusFilter = document.getElementById('statusFilter');
  const rows = Array.from(document.querySelectorAll('#tenderTable tbody tr'));

  function applyFilters() {
    const term = (search.value || '').toLowerCase();
    const status = statusFilter.value;

    rows.forEach((row) => {
      const text = row.textContent.toLowerCase();
      const matchesTerm = text.includes(term);
      const matchesStatus = !status || row.dataset.status === status;
      row.style.display = matchesTerm && matchesStatus ? '' : 'none';
    });
  }

  search.addEventListener('input', applyFilters);
  statusFilter.addEventListener('change', applyFilters);
});
