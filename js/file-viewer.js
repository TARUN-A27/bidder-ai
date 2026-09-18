/* The frozen API exposes evidence metadata, but no document-content route. */
(function () {
  function openCertificateFile() {
    if (window.showToast) {
      window.showToast('A document-content endpoint is not available in the frozen API.');
    }
  }
  document.addEventListener('click', (event) => {
    if (event.target.closest('[data-open-file]')) openCertificateFile();
  });
  window.openCertificateFile = openCertificateFile;
})();
