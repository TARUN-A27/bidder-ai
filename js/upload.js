document.addEventListener('DOMContentLoaded', async () => {
  const { get, postMultipart } = window.BidGuardAPI;
  const { params, page } = window.BidGuardNav;
  const { clear, el } = window.BidGuardUI;
  const tenderId = params().get('tender_id');
  const form = document.getElementById('importForm');
  const mode = document.getElementById('importMode');
  const input = document.getElementById('fileInput');
  const fileList = document.getElementById('fileList');
  const count = document.getElementById('fileCount');
  const state = document.getElementById('uploadState');
  const submit = document.getElementById('importButton');
  const result = document.getElementById('importResult');
  const dropzone = document.getElementById('dropzone');
  const files = new Map();

  if (!tenderId) {
    state.className = 'api-state error';
    state.textContent = 'Missing tender_id. Return to the dashboard and select a tender.';
    submit.disabled = true;
  }
  document.getElementById('backLink').href = page('tender-detail.html', { tender_id: tenderId });
  document.getElementById('tenderNavLink').href = page('tender-detail.html', { tender_id: tenderId });
  document.getElementById('comparisonNav').href = page('comparison.html', { tender_id: tenderId });
  if (tenderId) {
    try {
      const tender = await get(`/tenders/${encodeURIComponent(tenderId)}`);
      document.getElementById('tenderContext').textContent = `${tender.bid_number || tender.dataset_id || tender.tender_id} · ${tender.title}`;
      document.getElementById('datasetId').value = tender.dataset_id || '';
    } catch (_) {
      document.getElementById('tenderContext').textContent = `TENDER · ${tenderId}`;
    }
  }

  function key(file) {
    return `${file.name}:${file.size}:${file.lastModified}`;
  }

  function configureMode() {
    files.clear();
    input.value = '';
    input.multiple = mode.value === 'files';
    input.accept = mode.value === 'zip' ? '.zip,application/zip' : '.pdf,application/pdf';
    document.getElementById('profileFields').hidden = mode.value === 'zip';
    document.querySelectorAll('#profileFields input, #profileFields textarea').forEach((field) => { field.disabled = mode.value === 'zip'; });
    document.getElementById('fileHelp').textContent = mode.value === 'zip'
      ? 'Select one ZIP containing bidder_profile.json and bidder PDFs.'
      : 'Select one or more PDFs. Bidder name and PAN reference are required.';
    document.getElementById('dropTitle').textContent = mode.value === 'zip'
      ? 'Drag & drop a bidder ZIP here'
      : 'Drag & drop bidder PDFs here';
    renderFiles();
  }

  function renderFiles() {
    clear(fileList);
    files.forEach((file, fileKey) => {
      const label = el('span', { text: file.name });
      const remove = el('button', { type: 'button', text: 'Remove', className: 'btn btn-sm' });
      remove.setAttribute('aria-label', `Remove ${file.name}`);
      remove.addEventListener('click', () => { files.delete(fileKey); renderFiles(); });
      fileList.append(el('div', { className: 'file-chip' }, [label, remove]));
    });
    count.textContent = `${files.size} selected`;
    const ready = files.size > 0;
    ['checkFormat', 'checkFiles'].forEach((id) => {
      const row = document.getElementById(id);
      row.classList.toggle('uploaded', ready);
      row.querySelector('.state').textContent = ready ? '✓' : '–';
    });
    const profileReady = mode.value === 'files' && (
      document.getElementById('bidderName').value.trim()
      && document.getElementById('panReference').value.trim()
    );
    const profileRow = document.getElementById('checkProfile');
    profileRow.classList.toggle('uploaded', Boolean(profileReady));
    profileRow.querySelector('.state').textContent = profileReady ? '✓' : '–';
    document.getElementById('checklistBadge').textContent = ready ? `${files.size} selected` : 'Waiting';
  }

  function addFiles(selectedFiles) {
    Array.from(selectedFiles || []).forEach((file) => files.set(key(file), file));
    if (mode.value === 'zip' && files.size > 1) {
      const last = Array.from(files.entries()).pop();
      files.clear();
      files.set(last[0], last[1]);
    }
    renderFiles();
    input.value = '';
  }

  input.addEventListener('change', () => addFiles(input.files));
  dropzone.addEventListener('click', (event) => { if (event.target !== input) input.click(); });
  dropzone.addEventListener('keydown', (event) => {
    if (event.key === 'Enter' || event.key === ' ') { event.preventDefault(); input.click(); }
  });
  ['dragenter', 'dragover'].forEach((name) => dropzone.addEventListener(name, (event) => {
    event.preventDefault(); dropzone.classList.add('drag-over');
  }));
  ['dragleave', 'drop'].forEach((name) => dropzone.addEventListener(name, (event) => {
    event.preventDefault(); dropzone.classList.remove('drag-over');
  }));
  dropzone.addEventListener('drop', (event) => addFiles(event.dataTransfer.files));
  ['bidderName', 'panReference'].forEach((id) => document.getElementById(id).addEventListener('input', renderFiles));
  mode.addEventListener('change', configureMode);

  function validate(selected) {
    if (!tenderId) return 'A tender must be selected.';
    if (!selected.length) return 'Select a submission package to import.';
    if (mode.value === 'zip') {
      if (selected.length !== 1 || !selected[0].name.toLowerCase().endsWith('.zip')) return 'ZIP import requires exactly one .zip file.';
    } else {
      if (selected.some((file) => !file.name.toLowerCase().endsWith('.pdf'))) return 'Multi-file import accepts PDF files only.';
      if (!document.getElementById('bidderName').value.trim() || !document.getElementById('panReference').value.trim()) return 'Bidder name and PAN reference are required.';
    }
    return '';
  }

  form.addEventListener('submit', async (event) => {
    event.preventDefault();
    const selected = Array.from(files.values());
    const validation = validate(selected);
    state.hidden = false;
    result.hidden = true;
    if (validation) {
      state.className = 'api-state error';
      state.textContent = validation;
      return;
    }
    const data = new FormData();
    let path;
    if (mode.value === 'zip') {
      data.append('file', selected[0], selected[0].name);
      path = `/tenders/${encodeURIComponent(tenderId)}/submissions/import-zip`;
    } else {
      selected.forEach((file) => data.append('files', file, file.name));
      const profile = {
        bidder_name: document.getElementById('bidderName').value.trim(),
        pan_reference: document.getElementById('panReference').value.trim(),
        is_synthetic: document.getElementById('isSynthetic').checked,
        mse_claimed: document.getElementById('mseClaimed').checked,
        startup_claimed: document.getElementById('startupClaimed').checked,
        nsic_claimed: document.getElementById('nsicClaimed').checked,
        emd_exemption_claimed: document.getElementById('emdExemptionClaimed').checked,
      };
      [
        ['dataset_id', 'datasetId'], ['bidder_reference', 'bidderReference'], ['entity_type', 'entityType'],
        ['registered_address', 'registeredAddress'], ['gst_reference', 'gstReference'], ['udyam_reference', 'udyamReference'],
        ['offered_make', 'offeredMake'], ['offered_model', 'offeredModel'],
      ].forEach(([field, id]) => {
        const value = document.getElementById(id).value.trim();
        if (value) profile[field] = value;
      });
      data.append('bidder_profile', JSON.stringify(profile));
      path = `/tenders/${encodeURIComponent(tenderId)}/submissions/import-files`;
    }
    submit.disabled = true;
    form.setAttribute('aria-busy', 'true');
    state.className = 'api-state';
    state.textContent = 'Uploading and validating bidder submission…';
    try {
      const imported = await postMultipart(path, data);
      state.className = 'api-state success';
      state.textContent = imported.duplicate_import
        ? 'This exact submission was already imported. The existing record was returned.'
        : 'Bidder submission imported successfully.';
      const profileRow = document.getElementById('checkProfile');
      profileRow.classList.add('uploaded');
      profileRow.querySelector('.state').textContent = '✓';
      clear(result);
      result.append(el('p', { text: `${imported.bidder_name}: ${imported.document_count} stored document(s).` }));
      const warnings = imported.warnings || [];
      if (warnings.length) {
        const list = el('ul', { className: 'import-warnings' });
        warnings.forEach((warning) => list.append(el('li', { text: warning })));
        result.append(el('div', { className: 'api-state', attrs: { role: 'status' } }, [el('strong', { text: 'Backend warnings' }), list]));
      }
      if (imported.ready_for_assessment) result.append(el('a', {
        className: 'btn btn-primary', text: 'Run Assessment',
        href: page('processing.html', { tender_id: imported.tender_id, submission_id: imported.submission_id, bidder_id: imported.bidder_id }),
      }));
      result.hidden = false;
    } catch (error) {
      state.className = 'api-state error';
      state.textContent = error.message || 'Import failed.';
    } finally {
      submit.disabled = false;
      form.setAttribute('aria-busy', 'false');
    }
  });

  configureMode();
});
