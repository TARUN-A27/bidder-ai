(function () {
  'use strict';
  const PERFORMANCE_DATA = {
    A: { bidder_name: 'Averonix Document Systems Private Limited', previous_contracts: 8, successfully_completed: 7, delayed_contracts: 1, active_contracts: 2, major_defaults: 0, quality_acceptance_rate: 96, historical_compliance_issues: 0, record_summary: 'Strong historical contract completion and quality performance with no major defaults recorded.', advisory: 'No significant historical performance concerns identified.', watch_for: ['Monitor delivery timelines due to one previous delayed contract.'] },
    B: { bidder_name: 'Meralune Imaging Technologies LLP', previous_contracts: 6, successfully_completed: 4, delayed_contracts: 2, active_contracts: 1, major_defaults: 0, quality_acceptance_rate: 84, historical_compliance_issues: 1, record_summary: 'Historical performance shows generally completed contracts, with multiple delivery delays and one previous compliance issue.', advisory: 'Review historical delivery performance and consider stronger milestone monitoring during contract execution.', watch_for: ['Repeated delivery delays', 'Previous compliance issue', 'Lower historical quality acceptance'] },
    C: { bidder_name: 'Kryvanta Office Automation Private Limited', previous_contracts: 5, successfully_completed: 2, delayed_contracts: 2, active_contracts: 0, major_defaults: 1, quality_acceptance_rate: 68, historical_compliance_issues: 3, record_summary: 'Historical records show delivery and quality concerns, multiple compliance issues, and a previous major contract default.', advisory: 'Historical performance indicates areas requiring enhanced due diligence before the Procurement Officer makes a decision.', watch_for: ['Previous major contract default', 'Multiple historical compliance issues', 'Repeated delivery problems', 'Lower historical quality acceptance'] },
  };
  const overlay = document.getElementById('ppOverlay');
  if (!overlay) return;
  const body = document.getElementById('ppBody');
  const name = document.getElementById('ppBidderName');
  const title = document.getElementById('ppTitle');
  const subtitle = document.getElementById('ppSubtitle') || overlay.querySelector('.sub2');
  const closeButton = document.getElementById('ppClose');
  let opener = null;
  let requestVersion = 0;

  function node(tag, className, text) {
    const element = document.createElement(tag);
    if (className) element.className = className;
    if (text !== undefined) element.textContent = String(text);
    return element;
  }
  function section(title, content) {
    const wrapper = node('section', 'pp-section');
    wrapper.append(node('h4', '', title), content);
    return wrapper;
  }
  function metric(value, label) {
    const wrapper = node('div', 'pp-metric');
    wrapper.append(node('div', 'n', value), node('div', 'l', label));
    return wrapper;
  }
  function loading() {
    const skeleton = node('div', 'pp-skeleton');
    [60, 100, 85, 100].forEach((width) => {
      const line = node('div', 'pp-skel-line');
      line.style.width = `${width}%`;
      skeleton.append(line);
    });
    return skeleton;
  }
  function success(data) {
    const wrapper = document.createDocumentFragment();
    const metrics = node('div', 'pp-metrics');
    metrics.append(
      metric(data.previous_contracts, 'Previous contracts'), metric(data.successfully_completed, 'Successfully completed'),
      metric(data.delayed_contracts, 'Delayed contracts'), metric(data.active_contracts, 'Active contracts'),
      metric(data.major_defaults, 'Major defaults'), metric(data.historical_compliance_issues, 'Historical compliance issues'),
      metric(`${data.quality_acceptance_rate}%`, 'Quality acceptance'),
    );
    wrapper.append(section('Performance summary', metrics));
    wrapper.append(section('Historical record summary', node('p', '', data.record_summary)));
    wrapper.append(section('Advisory', node('p', '', data.advisory)));
    const list = node('ul');
    (data.watch_for || []).forEach((item) => list.append(node('li', '', item)));
    wrapper.append(section('Watch For', list.children.length ? list : node('p', '', 'No specific watch items identified.')));
    return wrapper;
  }
  function unavailableInsight(data) {
    const wrapper = document.createDocumentFragment();
    const state = node('div', 'ai-unavailable');
    state.append(node('span', 'badge badge-ink', 'AI provider unavailable'));
    state.append(node('h4', '', 'AI Bidder Performance Insight is not connected'));
    state.append(node('p', '', 'No secure server-side bidder-performance AI provider or endpoint is available in this build. Static history is not presented as AI-generated analysis.'));
    wrapper.append(state);
    const availability = node('div', 'pp-metrics');
    availability.append(
      metric(data ? 'Available' : 'Unavailable', 'Synthetic history'),
      metric('Unavailable', 'AI confidence'),
    );
    wrapper.append(section('Data availability', availability));
    wrapper.append(section('Procurement Officer note', node('p', '', 'Review the synthetic Previous Performance record separately. It does not affect the compliance score, risk, recommendation, comparison order, or officer decision.')));
    return wrapper;
  }
  function fetchPerformance(key) {
    return new Promise((resolve, reject) => window.setTimeout(() => {
      if (key === 'ERR') reject(new Error('Unavailable'));
      else resolve(PERFORMANCE_DATA[key] || null);
    }, 300));
  }
  async function load(key, version) {
    body.replaceChildren(loading());
    try {
      const data = await fetchPerformance(key);
      if (version !== requestVersion) return;
      if (!data) {
        body.replaceChildren(node('div', 'pp-empty', 'Historical performance data is not available for this bidder.'));
        return;
      }
      name.textContent = data.bidder_name;
      body.replaceChildren(success(data));
    } catch (_) {
      if (version !== requestVersion) return;
      const error = node('div', 'pp-error', 'Unable to load historical performance.');
      const retry = node('button', 'pp-btn', 'Retry');
      retry.type = 'button';
      retry.addEventListener('click', () => load(key, ++requestVersion));
      error.append(retry);
      body.replaceChildren(error);
    }
  }
  function open(trigger) {
    opener = trigger;
    const insight = trigger.hasAttribute('data-ai-insight-open');
    const key = trigger.dataset.ppBidder || '';
    const data = PERFORMANCE_DATA[key] || null;
    name.textContent = trigger.dataset.ppName || 'Selected bidder';
    title.textContent = insight ? 'AI Bidder Performance Insight' : 'Previous Performance';
    subtitle.textContent = insight ? 'Advisory integration status' : 'Synthetic demo performance history';
    overlay.classList.add('open');
    overlay.setAttribute('aria-hidden', 'false');
    Array.from(document.body.children).filter((item) => item !== overlay).forEach((item) => { item.inert = true; });
    document.body.style.overflow = 'hidden';
    closeButton.focus();
    if (insight) {
      requestVersion += 1;
      body.replaceChildren(unavailableInsight(data));
    } else {
      load(key, ++requestVersion);
    }
  }
  function close() {
    requestVersion += 1;
    overlay.classList.remove('open');
    overlay.setAttribute('aria-hidden', 'true');
    Array.from(document.body.children).filter((item) => item !== overlay).forEach((item) => { item.inert = false; });
    document.body.style.overflow = '';
    if (opener) opener.focus();
  }
  document.addEventListener('click', (event) => {
    const trigger = event.target.closest('[data-pp-open], [data-ai-insight-open]');
    if (trigger) open(trigger);
  });
  closeButton.addEventListener('click', close);
  overlay.addEventListener('click', (event) => { if (event.target === overlay) close(); });
  document.addEventListener('keydown', (event) => {
    if (!overlay.classList.contains('open')) return;
    if (event.key === 'Escape') close();
    if (event.key === 'Tab') {
      const focusable = Array.from(overlay.querySelectorAll('button, a[href], input, select, textarea, [tabindex]:not([tabindex="-1"])')).filter((item) => !item.disabled);
      if (!focusable.length) return;
      const first = focusable[0]; const last = focusable[focusable.length - 1];
      if (event.shiftKey && document.activeElement === first) { event.preventDefault(); last.focus(); }
      else if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first.focus(); }
    }
  });
})();
