/* ============================================================
   MAIN.JS — shared behaviour across every page
   ============================================================ */

// ---- officer account dropdown ----
document.addEventListener('click', (e) => {
  const btn = document.querySelector('[data-officer-btn]');
  const dropdown = document.querySelector('[data-officer-dropdown]');
  if (!btn || !dropdown) return;

  if (btn.contains(e.target)) {
    const open = dropdown.classList.toggle('open');
    btn.setAttribute('aria-expanded', String(open));
  } else if (!dropdown.contains(e.target)) {
    dropdown.classList.remove('open');
    btn.setAttribute('aria-expanded', 'false');
  }
});

document.addEventListener('keydown', (event) => {
  if (event.key !== 'Escape') return;
  const btn = document.querySelector('[data-officer-btn]');
  const dropdown = document.querySelector('[data-officer-dropdown]');
  if (btn && dropdown?.classList.contains('open')) {
    dropdown.classList.remove('open');
    btn.setAttribute('aria-expanded', 'false');
    btn.focus();
  }
});

// ---- toast helper (window.showToast('message')) ----
function showToast(message, duration = 2600) {
  let toast = document.querySelector('.toast');
  if (!toast) {
    toast = document.createElement('div');
    toast.className = 'toast';
    document.body.appendChild(toast);
  }
  toast.textContent = message;
  requestAnimationFrame(() => toast.classList.add('show'));
  clearTimeout(toast._timer);
  toast._timer = setTimeout(() => toast.classList.remove('show'), duration);
}
window.showToast = showToast;

// ---- simple modal open/close helper ----
function bindModal(triggerSelector, modalSelector) {
  const modal = document.querySelector(modalSelector);
  if (!modal) return;
  document.querySelectorAll(triggerSelector).forEach((trigger) => {
    trigger.addEventListener('click', () => modal.classList.add('open'));
  });
  modal.querySelectorAll('[data-close-modal]').forEach((el) => {
    el.addEventListener('click', () => modal.classList.remove('open'));
  });
  modal.addEventListener('click', (e) => {
    if (e.target === modal) modal.classList.remove('open');
  });
}
window.bindModal = bindModal;

// ---- log out confirmation ----
document.addEventListener('DOMContentLoaded', () => {
  document.body.classList.add('page-ready');
  const officerButton = document.querySelector('[data-officer-btn]');
  if (officerButton) {
    officerButton.setAttribute('aria-haspopup', 'menu');
    officerButton.setAttribute('aria-expanded', 'false');
  }
  const logoutLink = document.querySelector('[data-logout]');
  if (logoutLink) {
    logoutLink.addEventListener('click', (e) => {
      e.preventDefault();
      window.location.href = 'index.html';
    });
  }
});
