document.addEventListener('DOMContentLoaded', async () => {
  const { get, postMultipart } = window.BidGuardAPI;
  const { params, page } = window.BidGuardNav;
  const { clear, el } = window.BidGuardUI;

  const tenderId = params().get('tender_id');

  const form = document.getElementById('importForm');
  const zipInput = document.getElementById('zipInput');
  const folderInput = document.getElementById('folderInput');
  const chooseZip = document.getElementById('chooseZip');
  const chooseFolder = document.getElementById('chooseFolder');
  const dropzone = document.getElementById('dropzone');

  const fileList = document.getElementById('fileList');
  const selectionLabel = document.getElementById('selectionLabel');
  const state = document.getElementById('uploadState');
  const submit = document.getElementById('importButton');
  const result = document.getElementById('importResult');

  const processingPanel = document.getElementById('processingPanel');
  const processingStage = document.getElementById('processingStage');
  const processingCurrent = document.getElementById('processingCurrent');
  const processingHint = document.getElementById('processingHint');

  let processingStageTimer = null;
  let processingEvidenceTimer = null;


  let selectedMode = null;
  const files = new Map();

  if (!tenderId) {
    state.className = 'api-state error';
    state.textContent =
      'Missing tender_id. Return to the dashboard and select a tender.';
    submit.disabled = true;
  }

  document.getElementById('backLink').href =
    page('tender-detail.html', { tender_id: tenderId });

  document.getElementById('tenderNavLink').href =
    page('tender-detail.html', { tender_id: tenderId });

  document.getElementById('comparisonNav').href =
    page('comparison.html', { tender_id: tenderId });

  if (tenderId) {
    try {
      const tender = await get(
        `/tenders/${encodeURIComponent(tenderId)}`
      );

      document.getElementById('tenderContext').textContent =
        `${tender.bid_number || tender.dataset_id || tender.tender_id} · ${tender.title}`;
    } catch (_) {
      document.getElementById('tenderContext').textContent =
        `TENDER · ${tenderId}`;
    }
  }

  function fileKey(file) {
    return file.webkitRelativePath
      || `${file.name}:${file.size}:${file.lastModified}`;
  }

  function setCheck(id, ready) {
    const row = document.getElementById(id);

    row.classList.toggle('uploaded', Boolean(ready));
    row.querySelector('.state').textContent = ready ? 'OK' : '–';
  }

  function resetIdentityCheck() {
    setCheck('checkProfile', false);
  }

  function renderFiles() {
    clear(fileList);

    files.forEach((file) => {
      const displayName =
        file.webkitRelativePath || file.name;

      fileList.append(
        el('div', { className: 'file-chip' }, [
          el('span', { text: displayName }),
        ])
      );
    });

    const ready = files.size > 0;

    setCheck('checkFormat', ready);
    setCheck('checkFiles', ready);

    if (!ready) {
      selectionLabel.textContent = 'Nothing selected.';
      document.getElementById('checklistBadge').textContent = 'Waiting';
      return;
    }

    if (selectedMode === 'zip') {
      selectionLabel.textContent =
        `${files.size} ZIP selected. Bidder packages will be detected automatically.`;
    } else {
      selectionLabel.textContent =
        `${files.size} PDF document(s) selected from the folder.`;
    }

    document.getElementById('checklistBadge').textContent =
      selectedMode === 'zip'
        ? 'ZIP ready'
        : `${files.size} PDFs`;
  }

  function selectZip(file) {
    files.clear();
    resetIdentityCheck();

    if (!file) {
      selectedMode = null;
      renderFiles();
      return;
    }

    selectedMode = 'zip';
    files.set(fileKey(file), file);

    state.className = 'api-state';
    state.textContent =
      'ZIP selected. BidGuard will detect bidder packages automatically.';

    renderFiles();
  }

  function selectFolder(fileCollection) {
    files.clear();
    resetIdentityCheck();

    const pdfs = Array.from(fileCollection || [])
      .filter((file) =>
        file.name.toLowerCase().endsWith('.pdf')
      );

    if (!pdfs.length) {
      selectedMode = null;
      state.className = 'api-state error';
      state.textContent =
        'The selected folder does not contain PDF evidence.';
      renderFiles();
      return;
    }

    selectedMode = 'folder';

    pdfs.forEach((file) => {
      files.set(fileKey(file), file);
    });

    state.className = 'api-state';
    state.textContent =
      'Folder selected. BidGuard will detect individual bidder packages automatically.';

    renderFiles();
  }

  chooseZip.addEventListener('click', () => {
    zipInput.click();
  });

  chooseFolder.addEventListener('click', () => {
    folderInput.click();
  });

  zipInput.addEventListener('change', () => {
    selectZip(zipInput.files && zipInput.files[0]);
    zipInput.value = '';
  });

  folderInput.addEventListener('change', () => {
    selectFolder(folderInput.files);
    folderInput.value = '';
  });

  dropzone.addEventListener('click', () => {
    zipInput.click();
  });

  dropzone.addEventListener('keydown', (event) => {
    if (event.key === 'Enter' || event.key === ' ') {
      event.preventDefault();
      zipInput.click();
    }
  });

  ['dragenter', 'dragover'].forEach((name) => {
    dropzone.addEventListener(name, (event) => {
      event.preventDefault();
      dropzone.classList.add('drag-over');
    });
  });

  ['dragleave', 'drop'].forEach((name) => {
    dropzone.addEventListener(name, (event) => {
      event.preventDefault();
      dropzone.classList.remove('drag-over');
    });
  });

  dropzone.addEventListener('drop', (event) => {
    const dropped = Array.from(event.dataTransfer.files || []);

    if (
      dropped.length !== 1
      || !dropped[0].name.toLowerCase().endsWith('.zip')
    ) {
      state.className = 'api-state error';
      state.textContent =
        'Drag-and-drop accepts one ZIP. Use "Choose folder" for a folder.';
      return;
    }

    selectZip(dropped[0]);
  });

  function validate() {
    if (!tenderId) {
      return 'A tender must be selected.';
    }

    if (!selectedMode || !files.size) {
      return 'Select a ZIP or bidder folder to import.';
    }

    if (selectedMode === 'zip') {
      const selected = Array.from(files.values());

      if (
        selected.length !== 1
        || !selected[0].name.toLowerCase().endsWith('.zip')
      ) {
        return 'Select exactly one ZIP archive.';
      }
    }

    if (selectedMode === 'folder') {
      const selected = Array.from(files.values());

      if (
        selected.some(
          (file) => !file.name.toLowerCase().endsWith('.pdf')
        )
      ) {
        return 'Folder import accepts PDF evidence only.';
      }

      if (
        selected.some(
          (file) => !file.webkitRelativePath
        )
      ) {
        return 'Folder structure could not be determined. Select the parent folder again.';
      }
    }

    return '';
  }

  function addAssessmentLink(container, submission) {
    if (!submission || !submission.ready_for_assessment) {
      return;
    }

    container.append(
      el('a', {
        className: 'btn btn-primary btn-sm',
        text: 'Run Assessment',
        href: page('processing.html', {
          tender_id: submission.tender_id,
          submission_id: submission.submission_id,
          bidder_id: submission.bidder_id,
        }),
      })
    );
  }

  function renderBulkResult(imported) {
    clear(result);

    const importedCount = imported.imported_count || 0;
    const duplicateCount = imported.duplicate_count || 0;
    const failedCount = imported.failed_count || 0;
    const packageCount = imported.package_count || 0;

    const summary = el('div', {
      className: failedCount ? 'api-state' : 'api-state success',
    });

    summary.append(
      el('strong', {
        text: `${packageCount} bidder package${packageCount === 1 ? '' : 's'} detected`,
      })
    );

    summary.append(
      el('p', {
        text:
          `${importedCount} imported · ` +
          `${duplicateCount} already imported · ` +
          `${failedCount} failed`,
      })
    );

    result.append(summary);

    (imported.items || []).forEach((item) => {
      const submission = item.submission;
      const isFailure = item.status === 'FAILED';
      const isDuplicate = item.status === 'DUPLICATE';

      const card = el('div', {
        className: isFailure
          ? 'api-state error'
          : 'api-state success',
      });

      const bidderName =
        submission?.bidder_name
        || item.package_label
        || 'Bidder package';

      let statusText;

      if (item.status === 'IMPORTED') {
        statusText = 'Imported successfully';
      } else if (isDuplicate) {
        statusText = 'Already imported';
      } else {
        statusText = 'Import failed';
      }

      card.append(
        el('strong', {
          text: `${bidderName} — ${statusText}`,
        })
      );

      if (submission) {
        card.append(
          el('p', {
            text:
              `${submission.document_count} stored document(s)` +
              (isDuplicate
                ? ' · Existing submission reused.'
                : ''),
          })
        );

        const warnings = submission.warnings || [];

        if (warnings.length) {
          const list = el('ul', {
            className: 'import-warnings',
          });

          warnings.forEach((warning) => {
            list.append(el('li', { text: warning }));
          });

          card.append(list);
        }

      }

      if (isFailure) {
        card.append(
          el('p', {
            text:
              item.error_message
              || item.error_code
              || 'Bidder package could not be imported.',
          })
        );
      }

      result.append(card);
    });

    result.hidden = false;

    const successfulPackages =
      importedCount + duplicateCount;

    if (successfulPackages > 0) {
      setCheck('checkProfile', true);
    }

    if (failedCount === 0) {
      state.className = 'api-state success';

      if (duplicateCount && importedCount === 0) {
        state.textContent =
          'All bidder packages were already imported. Existing submissions are ready to use.';
      } else if (duplicateCount) {
        state.textContent =
          'Import completed. Existing bidder submissions were reused where duplicates were detected.';
      } else {
        state.textContent =
          'Bidder evidence imported successfully.';
      }
    } else if (successfulPackages > 0) {
      state.className = 'api-state';
      state.textContent =
        `Import completed with ${failedCount} failed bidder package(s). Review the results below.`;
    } else {
      state.className = 'api-state error';
      state.textContent =
        'No bidder packages could be imported.';
    }
  }


  function clearProcessingTimers() {
    if (processingStageTimer) {
      window.clearInterval(processingStageTimer);
      processingStageTimer = null;
    }

    if (processingEvidenceTimer) {
      window.clearInterval(processingEvidenceTimer);
      processingEvidenceTimer = null;
    }
  }

  function changeProcessingStage(text) {
    processingStage.classList.add('stage-changing');

    window.setTimeout(() => {
      processingStage.textContent = text;
      processingStage.classList.remove('stage-changing');
    }, 160);
  }

  function changeProcessingEvidence(text) {
    processingCurrent.classList.add('file-changing');

    window.setTimeout(() => {
      processingCurrent.textContent = text;
      processingCurrent.classList.remove('file-changing');
    }, 140);
  }

  function startProcessingAnimation(selectedFiles) {
    clearProcessingTimers();

    processingPanel.hidden = false;
    processingPanel.classList.remove(
      'processing-success',
      'processing-error'
    );

    const stages = [
      'Uploading bidder evidence…',
      'Discovering bidder packages…',
      'Classifying uploaded documents…',
      'Extracting bidder identity…',
      'Cross-checking PAN, GST and Udyam evidence…',
      'Checking existing submissions in Oracle…',
      'Preparing bidder import results…',
    ];

    const evidenceNames = selectedFiles
      .map((file) => file.webkitRelativePath || file.name)
      .filter(Boolean);

    let stageIndex = 0;
    let evidenceIndex = 0;

    processingStage.textContent = stages[0];

    if (selectedMode === 'zip') {
      const zipName = evidenceNames[0] || 'Bidder ZIP';

      processingCurrent.textContent = zipName;
      processingHint.textContent =
        'BidGuard is discovering bidder folders and PDF evidence inside this archive.';
    } else {
      processingCurrent.textContent =
        evidenceNames[0] || 'Selected bidder evidence';

      processingHint.textContent =
        `${evidenceNames.length} PDF document(s) selected. BidGuard is discovering bidder packages automatically.`;
    }

    processingStageTimer = window.setInterval(() => {
      stageIndex = Math.min(stageIndex + 1, stages.length - 1);
      changeProcessingStage(stages[stageIndex]);

      if (stageIndex === stages.length - 1) {
        window.clearInterval(processingStageTimer);
        processingStageTimer = null;
      }
    }, 2500);

    if (selectedMode === 'folder' && evidenceNames.length > 1) {
      processingEvidenceTimer = window.setInterval(() => {
        evidenceIndex = (evidenceIndex + 1) % evidenceNames.length;
        changeProcessingEvidence(evidenceNames[evidenceIndex]);
      }, 1250);
    }
  }

  function finishProcessingAnimation(kind, message) {
    clearProcessingTimers();

    if (!processingPanel) {
      return;
    }

    processingPanel.classList.remove(
      'processing-success',
      'processing-error'
    );

    if (kind === 'success') {
      processingPanel.classList.add('processing-success');
      processingStage.textContent = 'Processing complete';
    } else {
      processingPanel.classList.add('processing-error');
      processingStage.textContent = 'Processing stopped';
    }

    processingCurrent.textContent = message;

    window.setTimeout(() => {
      processingPanel.hidden = true;
    }, 1100);
  }

  form.addEventListener('submit', async (event) => {
    event.preventDefault();

    const validation = validate();

    state.hidden = false;
    result.hidden = true;

    if (validation) {
      state.className = 'api-state error';
      state.textContent = validation;
      return;
    }

    const data = new FormData();
    let path;

    if (selectedMode === 'zip') {
      const file = Array.from(files.values())[0];

      data.append('file', file, file.name);

      path =
        `/tenders/${encodeURIComponent(tenderId)}` +
        '/submissions/import-bulk-zip';
    } else {
      Array.from(files.values()).forEach((file) => {
        data.append(
          'files',
          file,
          file.webkitRelativePath || file.name
        );
      });

      path =
        `/tenders/${encodeURIComponent(tenderId)}` +
        '/submissions/import-folder';
    }

    submit.disabled = true;
    chooseZip.disabled = true;
    chooseFolder.disabled = true;

    form.setAttribute('aria-busy', 'true');

    state.hidden = true;

    const evidenceBeingProcessed = Array.from(files.values());

    startProcessingAnimation(evidenceBeingProcessed);

    const originalButtonText = submit.textContent;
    submit.textContent = 'Processing evidence…';

    try {
      const imported = await postMultipart(path, data);

      finishProcessingAnimation(
        'success',
        'Bidder evidence processed successfully.'
      );

      state.hidden = false;
      renderBulkResult(imported);
    } catch (error) {
      finishProcessingAnimation(
        'error',
        error.message || 'Bidder evidence import failed.'
      );

      state.hidden = false;
      state.className = 'api-state error';
      state.textContent =
        error.message || 'Bidder evidence import failed.';
    } finally {
      submit.disabled = false;
      chooseZip.disabled = false;
      chooseFolder.disabled = false;

      submit.textContent =
        typeof originalButtonText !== 'undefined'
          ? originalButtonText
          : 'Import bidder evidence';

      form.setAttribute('aria-busy', 'false');
    }
  });

  renderFiles();
});
