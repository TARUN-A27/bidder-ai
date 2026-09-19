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
    toast.setAttribute('role', 'status');
    toast.setAttribute('aria-live', 'polite');
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
  const officerDropdown = document.querySelector('[data-officer-dropdown]');
  if (officerButton) {
    officerButton.setAttribute('aria-haspopup', 'menu');
    officerButton.setAttribute('aria-expanded', 'false');
    if (officerDropdown) {
      officerDropdown.id ||= 'officer-menu';
      officerDropdown.setAttribute('role', 'menu');
      officerButton.setAttribute('aria-controls', officerDropdown.id);
      const menuItems = Array.from(officerDropdown.querySelectorAll('a'));
      menuItems.forEach((link) => link.setAttribute('role', 'menuitem'));
      officerButton.addEventListener('keydown', (event) => {
        if (!['ArrowDown', 'ArrowUp', 'Home', 'End'].includes(event.key) || !menuItems.length) return;
        event.preventDefault();
        officerDropdown.classList.add('open');
        officerButton.setAttribute('aria-expanded', 'true');
        const last = event.key === 'ArrowUp' || event.key === 'End';
        menuItems[last ? menuItems.length - 1 : 0].focus();
      });
      officerDropdown.addEventListener('keydown', (event) => {
        if (!['ArrowDown', 'ArrowUp', 'Home', 'End'].includes(event.key) || !menuItems.length) return;
        event.preventDefault();
        const current = Math.max(0, menuItems.indexOf(document.activeElement));
        const next = event.key === 'Home' ? 0
          : event.key === 'End' ? menuItems.length - 1
            : (current + (event.key === 'ArrowDown' ? 1 : -1) + menuItems.length) % menuItems.length;
        menuItems[next].focus();
      });
    }
  }
  const logoutLink = document.querySelector('[data-logout]');
  if (logoutLink) {
    logoutLink.addEventListener('click', (e) => {
      e.preventDefault();
      window.location.href = 'index.html';
    });
  }
});
