/* ============================================================
   INVESTIGATION.JS
   ============================================================ */
document.addEventListener('DOMContentLoaded', () => {

  /* ---- subtab switching ---- */
  const tabButtons = document.querySelectorAll('.subtabs button');
  tabButtons.forEach((btn) => {
    btn.addEventListener('click', () => {
      tabButtons.forEach((b) => b.classList.remove('active'));
      document.querySelectorAll('.tabpanel').forEach((p) => p.classList.remove('active'));
      btn.classList.add('active');
      document.getElementById(`panel-${btn.dataset.tab}`).classList.add('active');
    });
  });

  /* ---- what-if simulator ---- */
  const baseScore = 84;
  const whatifInputs = document.querySelectorAll('[data-whatif]');
  const simScore = document.getElementById('simScore');
  const simRisk = document.getElementById('simRisk');

  function recalc() {
    let score = baseScore;
    whatifInputs.forEach((input) => {
      if (input.checked) score += Number(input.dataset.whatif);
    });
    score = Math.min(score, 100);
    simScore.textContent = score;

    let riskHtml = '<span class="badge badge-red">High</span>';
    if (score >= 90) riskHtml = '<span class="badge badge-green">Low</span>';
    else if (score >= 70) riskHtml = '<span class="badge badge-amber">Medium</span>';
    simRisk.innerHTML = riskHtml;
  }
  whatifInputs.forEach((input) => input.addEventListener('change', recalc));

  /* ---- AI copilot (canned responses over tender evidence) ---- */
  const chatLog = document.getElementById('chatLog');
  const chatForm = document.getElementById('chatForm');
  const chatInput = document.getElementById('chatInput');
  const suggestionChips = document.querySelectorAll('[data-q]');

  const responses = [
    {
      match: /risk|medium/i,
      html: `XYZ Enterprises has 2 mandatory issues on file:
        <ul>
          <li>PAN ↔ GST company-name mismatch (94% confidence)</li>
          <li>OEM authorization letter unreadable — needs manual review</li>
        </ul>
        Risk = <strong>MEDIUM</strong>. Evidence is available in the Evidence Viewer tab.`,
    },
    {
      match: /evidence|mismatch|support/i,
      html: `The mismatch is based on Exhibit A (PAN card, legal name "ABC Technologies Pvt Ltd") versus Exhibit B (GST certificate, legal name "ABC Technology Solutions"). Udyam records (Exhibit C) match the PAN name, which supports treating the GST record as the outlier pending clarification.`,
    },
    {
      match: /resolve|fix|what would/i,
      html: `Two actions would move this bidder toward LOW risk:
        <ul>
          <li>A name-change certificate or clarification reconciling the PAN/GST names</li>
          <li>A legible, re-uploaded OEM authorization letter</li>
        </ul>
        You can preview the score impact in the What-if simulator tab.`,
    },
  ];

  function addMessage(role, html) {
    const msg = document.createElement('div');
    msg.className = `msg ${role}`;
    msg.innerHTML = `<div class="avatar">${role === 'ai' ? 'AI' : 'RS'}</div><div class="bubble">${html}</div>`;
    chatLog.appendChild(msg);
    chatLog.scrollTop = chatLog.scrollHeight;
  }

  function respondTo(question) {
    addMessage('officer', question);
    const found = responses.find((r) => r.match.test(question));
    const answer = found
      ? found.html
      : `I can only answer using the tender requirements and verified evidence on file for this bidder. Try asking about risk level, the evidence for a specific discrepancy, or what would resolve an issue.`;
    setTimeout(() => addMessage('ai', answer), 450);
  }

  suggestionChips.forEach((chip) => {
    chip.addEventListener('click', () => respondTo(chip.dataset.q));
  });

  chatForm.addEventListener('submit', (e) => {
    e.preventDefault();
    const value = chatInput.value.trim();
    if (!value) return;
    respondTo(value);
    chatInput.value = '';
  });
});
