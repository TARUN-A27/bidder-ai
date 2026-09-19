(function () {
  'use strict';

  const PERFORMANCE_DATA = {
    A: {
      bidder_name: 'Averonix Document Systems Private Limited',
      previous_contracts: 8,
      successfully_completed: 7,
      delayed_contracts: 1,
      active_contracts: 2,
      major_defaults: 0,
      quality_acceptance_rate: 96,
      historical_compliance_issues: 0,
      record_summary: 'Strong historical contract completion and quality performance with no major defaults recorded.',
      advisory: 'No significant historical performance concerns identified.',
      watch_for: ['Monitor delivery timelines due to one previous delayed contract.'],
    },
    B: {
      bidder_name: 'Meralune Imaging Technologies LLP',
      previous_contracts: 6,
      successfully_completed: 4,
      delayed_contracts: 2,
      active_contracts: 1,
      major_defaults: 0,
      quality_acceptance_rate: 84,
      historical_compliance_issues: 1,
      record_summary: 'Historical performance shows generally completed contracts, with multiple delivery delays and one previous compliance issue.',
      advisory: 'Review historical delivery performance and consider stronger milestone monitoring during contract execution.',
      watch_for: ['Repeated delivery delays', 'Previous compliance issue', 'Lower historical quality acceptance'],
    },
    C: {
      bidder_name: 'Kryvanta Office Automation Private Limited',
      previous_contracts: 5,
      successfully_completed: 2,
      delayed_contracts: 2,
      active_contracts: 0,
      major_defaults: 1,
      quality_acceptance_rate: 68,
      historical_compliance_issues: 3,
      record_summary: 'Historical records show delivery and quality concerns, multiple compliance issues, and a previous major contract default.',
      advisory: 'Historical performance indicates areas requiring enhanced due diligence before the Procurement Officer makes a decision.',
      watch_for: ['Previous major contract default', 'Multiple historical compliance issues', 'Repeated delivery problems', 'Lower historical quality acceptance'],
    },
  };

  const overlay = document.getElementById('ppOverlay');
  if (!overlay) return;

  const body = document.getElementById('ppBody');
  const name = document.getElementById('ppBidderName');
  const title = document.getElementById('ppTitle');
  const subtitle = document.getElementById('ppSubtitle') || overlay.querySelector('.sub2');
  const closeButton = document.getElementById('ppClose');
  const { postJson } = window.BidGuardAPI || {};
  const configuredAIPath = String(
    window.BIDGUARD_AI_PERFORMANCE_PATH
      || window.localStorage.getItem('bidguard.aiPerformancePath')
      || '',
  ).trim();

  let opener = null;
  let requestVersion = 0;

  function node(tag, className, text) {
    const element = document.createElement(tag);
    if (className) element.className = className;
    if (text !== undefined) element.textContent = String(text);
    return element;
  }

  function section(sectionTitle, content) {
    const wrapper = node('section', 'pp-section');
    wrapper.append(node('h4', '', sectionTitle), content);
    return wrapper;
  }

  function metric(value, label) {
    const wrapper = node('div', 'pp-metric');
    wrapper.append(node('div', 'n', value), node('div', 'l', label));
    return wrapper;
  }

  function list(items, emptyText) {
    const values = Array.isArray(items) ? items.filter((item) => String(item || '').trim()) : [];
    if (!values.length) return node('p', 'text-muted', emptyText);
    const result = node('ul');
    values.forEach((item) => result.append(node('li', '', item)));
    return result;
  }

  function loading(label = 'Loading bidder performance…') {
    const wrapper = node('div', 'pp-skeleton');
    wrapper.setAttribute('role', 'status');
    wrapper.setAttribute('aria-label', label);
    [60, 100, 85, 100].forEach((width) => {
      const line = node('div', 'pp-skel-line');
      line.style.width = `${width}%`;
      wrapper.append(line);
    });
    return wrapper;
  }

  function historicalMetrics(data) {
    const metrics = node('div', 'pp-metrics');
    metrics.append(
      metric(data.previous_contracts, 'Previous contracts'),
      metric(data.successfully_completed, 'Successfully completed'),
      metric(data.delayed_contracts, 'Delayed contracts'),
      metric(data.active_contracts, 'Active contracts'),
      metric(data.major_defaults, 'Major defaults'),
      metric(data.historical_compliance_issues, 'Historical compliance issues'),
      metric(`${data.quality_acceptance_rate}%`, 'Quality acceptance'),
    );
    return metrics;
  }

  function historicalView(data) {
    const wrapper = document.createDocumentFragment();
    wrapper.append(section('Performance summary', historicalMetrics(data)));
    wrapper.append(section('Historical record summary', node('p', '', data.record_summary)));
    wrapper.append(section('Advisory', node('p', '', data.advisory)));
    wrapper.append(section('Watch For', list(data.watch_for, 'No specific watch items identified.')));
    return wrapper;
  }

  function aiInsightView(data, insight) {
    const wrapper = document.createDocumentFragment();

    const panel = node('div', 'ai-insight-panel');

    const header = node('div', 'ai-insight-heading');

    header.append(
      node(
        'span',
        'badge badge-ink',
        `${insight.model || 'Qwen3:8B'} · Local AI`
      )
    );

    header.append(
      node(
        'span',
        'ai-advisory-label',
        'Advisory only'
      )
    );

    panel.append(header);

    panel.append(
      node(
        'div',
        'ai-insight-kicker',
        'AI PERFORMANCE ANALYSIS'
      )
    );

    panel.append(
      node(
        'p',
        'ai-insight-summary',
        insight.summary
      )
    );

    wrapper.append(panel);

    wrapper.append(
      section(
        'Grounded observations',
        list(
          insight.observations,
          'No grounded observations were returned.'
        )
      )
    );

    wrapper.append(
      section(
        'Procurement Officer review',
        list(
          insight.review_points,
          'No specific historical review points were identified.'
        )
      )
    );

    wrapper.append(
      section(
        'Historical data used',
        historicalMetrics(data)
      )
    );

    const boundary = node('div', 'ai-advisory-boundary');

    boundary.append(
      node(
        'strong',
        '',
        'Decision-support boundary'
      )
    );

    boundary.append(
      node(
        'p',
        '',
        'This AI analysis uses available historical performance data only. '
        + 'It does not change the compliance score, tender risk, comparison '
        + 'order, recommendation, or Procurement Officer decision.'
      )
    );

    wrapper.append(boundary);

    return wrapper;
  }

  let aiActivityTimer = null;

  function stopAIActivity() {
    if (aiActivityTimer) {
      window.clearInterval(aiActivityTimer);
      aiActivityTimer = null;
    }
  }

  function aiThinkingView(data) {
    const wrapper = document.createDocumentFragment();

    const panel = node('div', 'ai-thinking-panel');

    const top = node('div', 'ai-thinking-top');

    const dots = node('div', 'ai-thinking-dots');
    dots.setAttribute('aria-hidden', 'true');

    dots.append(
      document.createElement('span'),
      document.createElement('span'),
      document.createElement('span')
    );

    const copy = node('div', 'ai-thinking-copy');

    copy.append(
      node(
        'strong',
        '',
        'BidGuard AI is analyzing historical performance'
      )
    );

    const activity = node(
      'div',
      'ai-thinking-activity',
      'Reviewing previous contract history…'
    );

    activity.id = 'ppAiActivity';

    copy.append(activity);

    top.append(dots, copy);
    panel.append(top);

    const facts = node('div', 'ai-thinking-facts');

    facts.append(
      node(
        'span',
        '',
        `${data.previous_contracts} previous contracts`
      ),
      node(
        'span',
        '',
        `${data.delayed_contracts} delayed`
      ),
      node(
        'span',
        '',
        `${data.major_defaults} major defaults`
      ),
      node(
        'span',
        '',
        `${data.quality_acceptance_rate}% quality acceptance`
      )
    );

    panel.append(facts);

    panel.append(
      node(
        'p',
        'ai-thinking-note',
        'Qwen3:8B is generating a concise advisory summary. '
        + 'Numerical observations and review points remain grounded '
        + 'in the recorded historical data.'
      )
    );

    wrapper.append(panel);

    return wrapper;
  }

  function startAIActivity(version) {
    stopAIActivity();

    const stages = [
      'Reviewing previous contract history…',
      'Checking completed and delayed contracts…',
      'Reviewing active contract context…',
      'Checking defaults and compliance history…',
      'Reviewing quality acceptance records…',
      'Preparing grounded performance advisory…',
    ];

    let index = 0;

    aiActivityTimer = window.setInterval(() => {
      if (version !== requestVersion) {
        stopAIActivity();
        return;
      }

      const activity = document.getElementById('ppAiActivity');

      if (!activity) {
        stopAIActivity();
        return;
      }

      index = Math.min(index + 1, stages.length - 1);

      activity.classList.add('changing');

      window.setTimeout(() => {
        if (version !== requestVersion) return;

        activity.textContent = stages[index];
        activity.classList.remove('changing');
      }, 130);

      if (index === stages.length - 1) {
        stopAIActivity();
      }
    }, 700);
  }

  function fetchPerformance(key) {
    return Promise.resolve(PERFORMANCE_DATA[key] || null);
  }

  const PERFORMANCE_AI_PATH = '/ai/performance-insight';

  function aiPayload(data, bidderName) {
    return {
      bidder_id: data.bidder_id || null,
      bidder_name: bidderName || data.bidder_name,

      previous_contracts: data.previous_contracts,
      successfully_completed: data.successfully_completed,
      delayed_contracts: data.delayed_contracts,
      active_contracts: data.active_contracts,
      major_defaults: data.major_defaults,
      historical_compliance_issues:
        data.historical_compliance_issues,
      quality_acceptance_rate:
        data.quality_acceptance_rate,
    };
  }

  function validateInsight(value) {
    if (!value || typeof value !== 'object') {
      throw new Error('AI provider returned an invalid response.');
    }

    if (
      typeof value.summary !== 'string'
      || !value.summary.trim()
    ) {
      throw new Error(
        'AI provider returned no performance summary.'
      );
    }

    const observations = Array.isArray(value.observations)
      ? value.observations
        .map(String)
        .map((item) => item.trim())
        .filter(Boolean)
      : [];

    const reviewPoints = Array.isArray(value.review_points)
      ? value.review_points
        .map(String)
        .map((item) => item.trim())
        .filter(Boolean)
      : [];

    if (!observations.length) {
      throw new Error(
        'AI performance response contained no grounded observations.'
      );
    }

    return {
      provider:
        typeof value.provider === 'string'
          ? value.provider
          : 'ollama',

      model:
        typeof value.model === 'string'
          ? value.model
          : 'qwen3:8b',

      summary: value.summary.trim(),

      observations,

      review_points: reviewPoints,

      advisory: value.advisory !== false,
    };
  }

  async function loadHistory(key, version) {
    body.replaceChildren(loading());
    try {
      const data = await fetchPerformance(key);
      if (version !== requestVersion) return;
      if (!data) {
        body.replaceChildren(node('div', 'pp-empty', 'Historical performance data is not available for this bidder.'));
        return;
      }
      name.textContent = data.bidder_name;
      body.replaceChildren(historicalView(data));
    } catch (_) {
      if (version !== requestVersion) return;
      const error = node('div', 'pp-error', 'Unable to load historical performance.');
      const retry = node('button', 'pp-btn', 'Retry');
      retry.type = 'button';
      retry.addEventListener('click', () => loadHistory(key, ++requestVersion));
      error.append(retry);
      body.replaceChildren(error);
    }
  }

  async function loadAIInsight(
    key,
    fallbackName,
    version
  ) {
    const data = PERFORMANCE_DATA[key] || null;

    if (!data) {
      body.replaceChildren(
        node(
          'div',
          'pp-empty',
          'AI insight cannot be generated because historical '
          + 'performance data is not available for this bidder.'
        )
      );

      return;
    }

    name.textContent =
      data.bidder_name
      || fallbackName
      || 'Selected bidder';

    if (typeof postJson !== 'function') {
      body.replaceChildren(
        node(
          'div',
          'pp-error',
          'BidGuard API client is unavailable.'
        )
      );

      return;
    }

    body.replaceChildren(aiThinkingView(data));

    startAIActivity(version);

    try {
      const response = await postJson(
        PERFORMANCE_AI_PATH,
        aiPayload(data, fallbackName)
      );

      if (version !== requestVersion) {
        stopAIActivity();
        return;
      }

      stopAIActivity();

      const insight = validateInsight(response);

      body.replaceChildren(
        aiInsightView(data, insight)
      );

    } catch (error) {
      if (version !== requestVersion) {
        stopAIActivity();
        return;
      }

      stopAIActivity();

      const errorState = node(
        'div',
        'pp-error'
      );

      errorState.append(
        node(
          'strong',
          '',
          'AI performance analysis is currently unavailable.'
        )
      );

      errorState.append(
        node(
          'p',
          'text-muted',
          error?.message
          || 'Local Qwen could not generate the advisory.'
        )
      );

      const retry = node(
        'button',
        'pp-btn',
        'Retry AI analysis'
      );

      retry.type = 'button';

      retry.addEventListener(
        'click',
        () => loadAIInsight(
          key,
          fallbackName,
          ++requestVersion
        )
      );

      errorState.append(retry);

      body.replaceChildren(errorState);
    }
  }

  function open(trigger) {
    opener = trigger;
    const insightMode = trigger.hasAttribute('data-ai-insight-open');
    const key = trigger.dataset.ppBidder || '';
    const fallbackName = trigger.dataset.ppName || 'Selected bidder';
    name.textContent = fallbackName;
    title.textContent = insightMode ? 'AI Bidder Performance Insight' : 'Previous Performance';
    subtitle.textContent = insightMode
      ? 'Local Qwen3:8B performance advisory'
      : 'Synthetic demo performance history';
    closeButton.setAttribute('aria-label', `Close ${insightMode ? 'AI Bidder Performance Insight' : 'Previous Performance'}`);
    overlay.classList.add('open');
    overlay.setAttribute('aria-hidden', 'false');
    Array.from(document.body.children).filter((item) => item !== overlay).forEach((item) => { item.inert = true; });
    document.body.style.overflow = 'hidden';
    closeButton.focus();
    const version = ++requestVersion;
    if (insightMode) loadAIInsight(key, fallbackName, version);
    else loadHistory(key, version);
  }

  function close() {
    requestVersion += 1;
    stopAIActivity();
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
    if (event.key === 'Escape') {
      event.preventDefault();
      close();
      return;
    }
    if (event.key === 'Tab') {
      const focusable = Array.from(overlay.querySelectorAll('button, a[href], input, select, textarea, [tabindex]:not([tabindex="-1"])')).filter((item) => !item.disabled);
      if (!focusable.length) return;
      const first = focusable[0];
      const last = focusable[focusable.length - 1];
      if (event.shiftKey && document.activeElement === first) {
        event.preventDefault();
        last.focus();
      } else if (!event.shiftKey && document.activeElement === last) {
        event.preventDefault();
        first.focus();
      }
    }
  });
})();
