/* ============================================================
   PROCESSING.JS — simulated step-by-step verification pipeline
   ============================================================ */
document.addEventListener('DOMContentLoaded', () => {
  const rows = Array.from(document.querySelectorAll('.pipe-row'));
  const progressFill = document.getElementById('progressFill');
  const stepCounter = document.getElementById('stepCounter');
  const etaLabel = document.getElementById('etaLabel');
  const overallStatus = document.getElementById('overallStatus');
  const doneActions = document.getElementById('doneActions');

  let current = 0;
  const total = rows.length;
  const stepDurationMs = 900;

  function setRowState(row, state) {
    row.classList.remove('active', 'done');
    const statusEl = row.querySelector('.status');
    const dot = row.querySelector('.dot');
    if (state === 'active') {
      row.classList.add('active');
      statusEl.textContent = 'Running…';
    } else if (state === 'done') {
      row.classList.add('done');
      statusEl.textContent = 'Complete';
      dot.textContent = '✓';
    } else {
      statusEl.textContent = 'Queued';
    }
  }

  function tick() {
    if (current > 0) setRowState(rows[current - 1], 'done');

    if (current >= total) {
      progressFill.style.width = '100%';
      stepCounter.textContent = `STEP ${total} / ${total}`;
      etaLabel.textContent = 'COMPLETE';
      overallStatus.textContent = 'Complete';
      overallStatus.className = 'badge badge-green';
      doneActions.style.display = 'block';
      return;
    }

    setRowState(rows[current], 'active');
    const pct = Math.round(((current + 0.5) / total) * 100);
    progressFill.style.width = pct + '%';
    stepCounter.textContent = `STEP ${current + 1} / ${total}`;
    const remaining = Math.max(0, Math.round(((total - current) * stepDurationMs) / 1000));
    etaLabel.textContent = `ESTIMATED TIME REMAINING: 00:${String(remaining).padStart(2, '0')}`;

    current++;
    setTimeout(tick, stepDurationMs);
  }

  setTimeout(tick, 400);
});
