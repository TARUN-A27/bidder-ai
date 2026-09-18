/* ============================================================
   PREVIOUS-PERFORMANCE.JS
   Reusable "Previous Performance" side drawer.

   This is DECISION-SUPPORT INFORMATION ONLY. It must never:
   - modify the current compliance score or risk level
   - modify requirement statuses
   - auto-qualify/disqualify a bidder or select a winner
   The Procurement Officer remains the final decision authority.

   TODO (backend): replace PERFORMANCE_DATA + fetchPerformance()
   below with a real API call, e.g.
     GET /api/bidders/:bidder_id/previous-performance
   keeping the same shape so the render functions don't change:
     {
       bidder_id, bidder_name,
       previous_contracts, successfully_completed, delayed_contracts,
       active_contracts, major_defaults, quality_acceptance_rate,
       historical_compliance_issues,
       performance_insight, advisory, watch_for: []
     }
   ============================================================ */
(function () {

  /* ---- temporary synthetic demo data (isolated from assessment data) ---- */
  const PERFORMANCE_DATA = {
    A: {
      bidder_id: 'A',
      bidder_name: 'ABC Technologies Pvt Ltd',
      previous_contracts: 8,
      successfully_completed: 7,
      delayed_contracts: 1,
      active_contracts: 2,
      major_defaults: 0,
      quality_acceptance_rate: 96,
      historical_compliance_issues: 0,
      performance_insight: 'Strong historical contract completion and quality performance with no major defaults recorded.',
      advisory: 'No significant historical performance concerns identified.',
      watch_for: ['Monitor delivery timelines due to one previous delayed contract.'],
    },
    B: {
      bidder_id: 'B',
      bidder_name: 'XYZ Enterprises',
      previous_contracts: 6,
      successfully_completed: 4,
      delayed_contracts: 2,
      active_contracts: 1,
      major_defaults: 0,
      quality_acceptance_rate: 84,
      historical_compliance_issues: 1,
      performance_insight: 'Historical performance shows generally completed contracts, with multiple delivery delays and one previous compliance issue.',
      advisory: 'Review historical delivery performance and consider stronger milestone monitoring during contract execution.',
      watch_for: ['Repeated delivery delays', 'Previous compliance issue', 'Lower historical quality acceptance'],
    },
    C: {
      bidder_id: 'C',
      bidder_name: 'LMN Corp',
      previous_contracts: 5,
      successfully_completed: 2,
      delayed_contracts: 2,
      active_contracts: 0,
      major_defaults: 1,
      quality_acceptance_rate: 68,
      historical_compliance_issues: 3,
      performance_insight: 'Historical records show delivery and quality concerns, multiple compliance issues, and a previous major contract default.',
      advisory: 'Historical performance indicates areas requiring enhanced due diligence before the Procurement Officer makes a decision.',
      watch_for: ['Previous major contract default', 'Multiple historical compliance issues', 'Repeated delivery problems', 'Lower historical quality acceptance'],
    },
    // deliberately absent: any other bidder key resolves to NO_DATA
  };

  /** Simulates an async API call. Swap this for a real fetch() later. */
  function fetchPerformance(bidderKey) {
    return new Promise((resolve, reject) => {
      setTimeout(() => {
        if (bidderKey === 'ERR') { reject(new Error('network')); return; }
        resolve(PERFORMANCE_DATA[bidderKey] || null);
      }, 500);
    });
  }

  /* ---- rendering per state ---- */
  function renderLoading() {
    return `
      <div class="pp-skeleton">
        <div class="pp-skel-line" style="width:60%;"></div>
        <div class="pp-metrics">
          <div class="pp-skel-line" style="height:64px;"></div>
          <div class="pp-skel-line" style="height:64px;"></div>
          <div class="pp-skel-line" style="height:64px;"></div>
          <div class="pp-skel-line" style="height:64px;"></div>
        </div>
        <div class="pp-skel-line" style="width:100%; height:60px;"></div>
        <div class="pp-skel-line" style="width:100%; height:40px;"></div>
      </div>`;
  }

  function renderNoData() {
    return `<div class="pp-empty">Historical performance data is not available for this bidder.</div>`;
  }

  function renderError() {
    return `
      <div class="pp-error">
        Unable to load historical performance.
        <div style="margin-top:12px;"><button type="button" class="pp-btn" id="ppRetry">Retry</button></div>
      </div>`;
  }

  function renderSuccess(d) {
    const watchItems = (d.watch_for || []).map((w) => `<li>${w}</li>`).join('');
    return `
      <div class="pp-section">
        <h4>Performance summary</h4>
        <div class="pp-metrics">
          <div class="pp-metric"><div class="n">${d.previous_contracts}</div><div class="l">Previous contracts</div></div>
          <div class="pp-metric"><div class="n">${d.successfully_completed}</div><div class="l">Successfully completed</div></div>
          <div class="pp-metric"><div class="n">${d.delayed_contracts}</div><div class="l">Delayed contracts</div></div>
          <div class="pp-metric"><div class="n">${d.active_contracts}</div><div class="l">Active contracts</div></div>
          <div class="pp-metric"><div class="n">${d.major_defaults}</div><div class="l">Major defaults</div></div>
          <div class="pp-metric"><div class="n">${d.historical_compliance_issues}</div><div class="l">Historical compliance issues</div></div>
          <div class="pp-metric wide"><div><div class="l" style="margin-top:0;">Quality acceptance</div></div><div class="n">${d.quality_acceptance_rate}%</div></div>
        </div>
      </div>
      <div class="pp-section">
        <h4>Performance insight</h4>
        <p>${d.performance_insight}</p>
      </div>
      <div class="pp-section">
        <h4>Advisory</h4>
        <p>${d.advisory}</p>
      </div>
      <div class="pp-section" style="margin-bottom:0;">
        <h4>Watch for</h4>
        ${watchItems ? `<ul>${watchItems}</ul>` : '<p>No specific watch items identified.</p>'}
      </div>`;
  }

  /* ---- drawer wiring ---- */
  const overlay = document.getElementById('ppOverlay');
  if (!overlay) return; // page doesn't include the drawer markup

  const bodyEl = document.getElementById('ppBody');
  const nameEl = document.getElementById('ppBidderName');
  const closeBtn = document.getElementById('ppClose');
  let currentKey = null;

  async function load(bidderKey) {
    bodyEl.innerHTML = renderLoading();
    try {
      const data = await fetchPerformance(bidderKey);
      if (!data) {
        bodyEl.innerHTML = renderNoData();
        return;
      }
      nameEl.textContent = data.bidder_name;
      bodyEl.innerHTML = renderSuccess(data);
    } catch (err) {
      bodyEl.innerHTML = renderError();
      const retryBtn = document.getElementById('ppRetry');
      if (retryBtn) retryBtn.addEventListener('click', () => load(bidderKey));
    }
  }

  function openDrawer(bidderKey, bidderNameFallback) {
    currentKey = bidderKey;
    nameEl.textContent = bidderNameFallback || '—';
    overlay.classList.add('open');
    document.body.style.overflow = 'hidden';
    load(bidderKey);
  }

  function closeDrawer() {
    overlay.classList.remove('open');
    document.body.style.overflow = '';
  }

  document.addEventListener('click', (e) => {
    const trigger = e.target.closest('[data-pp-open]');
    if (trigger) {
      openDrawer(trigger.dataset.ppBidder, trigger.dataset.ppName);
    }
  });

  closeBtn.addEventListener('click', closeDrawer);
  overlay.addEventListener('click', (e) => { if (e.target === overlay) closeDrawer(); });
  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape' && overlay.classList.contains('open')) closeDrawer();
  });
})();
