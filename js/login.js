/* ============================================================
   LOGIN.JS — single Procurement Officer sign-in
   ============================================================ */
document.addEventListener('DOMContentLoaded', () => {
  const form = document.getElementById('loginForm');
  form.addEventListener('submit', (e) => {
    e.preventDefault();
    const submitBtn = form.querySelector('button[type="submit"]');
    submitBtn.disabled = true;
    submitBtn.textContent = 'Verifying credentials…';
    setTimeout(() => {
      window.location.href = 'dashboard.html';
    }, 550);
  });
});
