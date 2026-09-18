/* BidGuard's small, shared API and navigation layer. */
(function () {
  'use strict';

  const configuredBase = window.BIDGUARD_API_BASE
    || window.localStorage.getItem('bidguard.apiBase')
    || '/api/v1';
  const apiBase = configuredBase.replace(/\/$/, '');

  class ApiError extends Error {
    constructor(message, status, body) {
      super(message);
      this.name = 'ApiError';
      this.status = status;
      this.body = body;
    }
  }

  function errorMessage(body, fallback) {
    if (!body || typeof body !== 'object') return fallback;
    const detail = body.detail;
    if (typeof detail === 'string' && detail.trim()) return detail;
    if (detail && !Array.isArray(detail) && typeof detail.message === 'string') {
      return detail.message;
    }
    if (Array.isArray(detail) && detail.length && typeof detail[0]?.msg === 'string') {
      return detail[0].msg;
    }
    return fallback;
  }

  async function request(path, options = {}) {
    let response;
    try {
      response = await fetch(`${apiBase}${path}`, {
        ...options,
        headers: { Accept: 'application/json', ...(options.headers || {}) },
      });
    } catch (_) {
      throw new ApiError('Unable to reach the BidGuard backend.', 0, null);
    }

    const text = await response.text();
    let body = null;
    if (text) {
      try {
        body = JSON.parse(text);
      } catch (_) {
        throw new ApiError(
          response.ok ? 'Backend returned an unexpected response.' : `Request failed (${response.status}).`,
          response.status,
          null,
        );
      }
    }
    if (!response.ok) {
      throw new ApiError(errorMessage(body, `Request failed (${response.status}).`), response.status, body);
    }
    return body;
  }

  function get(path) {
    return request(path);
  }

  function postJson(path, value) {
    return request(path, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(value),
    });
  }

  function postMultipart(path, formData) {
    return request(path, { method: 'POST', body: formData });
  }

  function post(path) {
    return request(path, { method: 'POST' });
  }

  function params() {
    return new URLSearchParams(window.location.search);
  }

  function page(path, values = {}) {
    const query = new URLSearchParams();
    Object.entries(values).forEach(([key, value]) => {
      if (value !== undefined && value !== null && value !== '') query.set(key, value);
    });
    const suffix = query.toString();
    return `${path}${suffix ? `?${suffix}` : ''}`;
  }

  function el(tag, options = {}, children = []) {
    const node = document.createElement(tag);
    Object.entries(options).forEach(([key, value]) => {
      if (key === 'className') node.className = value;
      else if (key === 'text') node.textContent = value == null ? '' : String(value);
      else if (key === 'dataset') Object.assign(node.dataset, value);
      else if (key === 'attrs') Object.entries(value).forEach(([name, attr]) => node.setAttribute(name, attr));
      else node[key] = value;
    });
    const list = Array.isArray(children) ? children : [children];
    list.filter(Boolean).forEach((child) => node.append(child));
    return node;
  }

  function clear(node) {
    node.replaceChildren();
  }

  function formatDate(value) {
    if (!value) return 'Not provided';
    const date = new Date(value);
    return Number.isNaN(date.getTime()) ? String(value) : date.toLocaleString();
  }

  const riskClasses = {
    LOW: 'badge badge-green',
    MEDIUM: 'badge badge-amber',
    HIGH: 'badge badge-orange',
    CRITICAL: 'badge badge-critical',
  };

  function riskBadge(risk) {
    const normalized = risk ? String(risk).toUpperCase() : 'PENDING';
    return el('span', { className: riskClasses[normalized] || 'badge badge-ink', text: normalized });
  }

  window.BidGuardAPI = { ApiError, apiBase, get, post, postJson, postMultipart };
  window.BidGuardNav = { params, page };
  window.BidGuardUI = { clear, el, errorMessage, formatDate, riskBadge };
})();
