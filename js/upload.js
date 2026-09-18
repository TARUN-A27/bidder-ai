/* ============================================================
   UPLOAD.JS — drag & drop + document checklist matching
   ============================================================ */
document.addEventListener('DOMContentLoaded', () => {
  const dropzone = document.getElementById('dropzone');
  const fileInput = document.getElementById('fileInput');
  const fileList = document.getElementById('fileList');
  const checklistRows = Array.from(document.querySelectorAll('.doc-row'));
  const checklistBadge = document.getElementById('checklistBadge');

  const keywordMap = {
    'GST Certificate': ['gst'],
    'PAN Card': ['pan'],
    'Udyam Certificate': ['udyam', 'msme'],
    'ITR': ['itr', 'income'],
    'OEM Authorization': ['oem'],
    'MII Declaration': ['mii', 'makeinindia', 'local'],
  };

  let uploadedCount = 0;

  function markChecklist(fileName) {
    const lower = fileName.toLowerCase();
    for (const row of checklistRows) {
      const doc = row.dataset.doc;
      if (row.classList.contains('uploaded')) continue;
      const keywords = keywordMap[doc] || [];
      if (keywords.some((k) => lower.includes(k))) {
        row.classList.add('uploaded');
        row.querySelector('.state').textContent = '✓';
        const filenameTag = document.createElement('span');
        filenameTag.className = 'filename';
        filenameTag.textContent = fileName;
        row.querySelector('.req').replaceWith(filenameTag);
        uploadedCount++;
        updateBadge();
        return;
      }
    }
  }

  function updateBadge() {
    checklistBadge.textContent = `${uploadedCount} / ${checklistRows.length} uploaded`;
    checklistBadge.className = uploadedCount >= checklistRows.length ? 'badge badge-green' : 'badge badge-amber';
  }

  function addFiles(fileArray) {
    fileArray.forEach((file) => {
      const chip = document.createElement('div');
      chip.className = 'file-chip';
      chip.innerHTML = `<span>📄 ${file.name}</span>`;
      const removeBtn = document.createElement('button');
      removeBtn.textContent = '✕';
      removeBtn.setAttribute('aria-label', `Remove ${file.name}`);
      removeBtn.addEventListener('click', () => chip.remove());
      chip.appendChild(removeBtn);
      fileList.appendChild(chip);
      markChecklist(file.name);
    });
    if (window.showToast) showToast(`${fileArray.length} file(s) added — running OCR classification…`);
  }

  dropzone.addEventListener('click', () => fileInput.click());
  fileInput.addEventListener('change', (e) => addFiles(Array.from(e.target.files)));

  ['dragenter', 'dragover'].forEach((evt) => {
    dropzone.addEventListener(evt, (e) => {
      e.preventDefault();
      dropzone.classList.add('drag-over');
    });
  });
  ['dragleave', 'drop'].forEach((evt) => {
    dropzone.addEventListener(evt, (e) => {
      e.preventDefault();
      dropzone.classList.remove('drag-over');
    });
  });
  dropzone.addEventListener('drop', (e) => {
    const files = Array.from(e.dataTransfer.files || []);
    if (files.length) addFiles(files);
  });
});
