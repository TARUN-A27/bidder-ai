(function () {
  'use strict';
  const PERFORMANCE_DATA = {
    A: { bidder_name: 'Averonix Document Systems Private Limited', previous_contracts: 8, successfully_completed: 7, delayed_contracts: 1, active_contracts: 2, major_defaults: 0, quality_acceptance_rate: 96, historical_compliance_issues: 0, performance_insight: 'Strong historical contract completion and quality performance with no major defaults recorded.', advisory: 'No significant historical performance concerns identified.', watch_for: ['Monitor delivery timelines due to one previous delayed contract.'] },
    B: { bidder_name: 'Meralune Imaging Technologies LLP', previous_contracts: 6, successfully_completed: 4, delayed_contracts: 2, active_contracts: 1, major_defaults: 0, quality_acceptance_rate: 84, historical_compliance_issues: 1, performance_insight: 'Historical performance shows generally completed contracts, with multiple delivery delays and one previous compliance issue.', advisory: 'Review historical delivery performance and consider stronger milestone monitoring during contract execution.', watch_for: ['Repeated delivery delays', 'Previous compliance issue', 'Lower historical quality acceptance'] },
    C: { bidder_name: 'Kryvanta Office Automation Private Limited', previous_contracts: 5, successfully_completed: 2, delayed_contracts: 2, active_contracts: 0, major_defaults: 1, quality_acceptance_rate: 68, historical_compliance_issues: 3, performance_insight: 'Historical records show delivery and quality concerns, multiple compliance issues, and a previous major contract default.', advisory: 'Historical performance indicates areas requiring enhanced due diligence before the Procurement Officer makes a decision.', watch_for: ['Previous major contract default', 'Multiple historical compliance issues', 'Repeated delivery problems', 'Lower historical quality acceptance'] },
  };
  const overlay = document.getElementById('ppOverlay');
  if (!overlay) return;
  const body = document.getElementById('ppBody');
  const name = document.getElementById('ppBidderName');
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
    wrapper.append(section('Performance Insight', node('p', '', data.performance_insight)));
    wrapper.append(section('Advisory', node('p', '', data.advisory)));
    const list = node('ul');
    (data.watch_for || []).forEach((item) => list.append(node('li', '', item)));
    wrapper.append(section('Watch For', list.children.length ? list : node('p', '', 'No specific watch items identified.')));
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
    name.textContent = trigger.dataset.ppName || 'Selected bidder';
    overlay.classList.add('open');
    overlay.setAttribute('aria-hidden', 'false');
    document.body.style.overflow = 'hidden';
    closeButton.focus();
    load(trigger.dataset.ppBidder || '', ++requestVersion);
  }
  function close() {
    requestVersion += 1;
    overlay.classList.remove('open');
    overlay.setAttribute('aria-hidden', 'true');
    document.body.style.overflow = '';
    if (opener) opener.focus();
  }
  document.addEventListener('click', (event) => {
    const trigger = event.target.closest('[data-pp-open]');
    if (trigger) open(trigger);
  });
  closeButton.addEventListener('click', close);
  overlay.addEventListener('click', (event) => { if (event.target === overlay) close(); });
  document.addEventListener('keydown', (event) => { if (event.key === 'Escape' && overlay.classList.contains('open')) close(); });
})();
