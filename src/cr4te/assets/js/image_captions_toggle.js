window.cr4te.onReady(function () {

  const STORAGE_KEY = "imageCaptionsEnabled";
  const sections = document.querySelectorAll(".image-caption-section");
  if (!sections.length) return;

  function loadCaptionsEnabled() {
    try {
      return localStorage.getItem(STORAGE_KEY) === "true";
    } catch {
      return false;
    }
  }

  function saveCaptionsEnabled(enabled) {
    try {
      localStorage.setItem(STORAGE_KEY, String(enabled));
    } catch {
      // Caption toggling still works for the current page.
    }
  }

  function updateCaptionTooltip(sectionBox) {
    const button = sectionBox.querySelector(".caption-toggle-btn");
    if (!button) return;

    const label = sectionBox.classList.contains("no-captions")
      ? button.dataset.showCaptionsLabel
      : button.dataset.hideCaptionsLabel;

    if (!label) return;
    button.title = label;
    button.setAttribute("aria-label", label);
  }

  // Restore state
  const captionsEnabled = loadCaptionsEnabled();

  sections.forEach(sectionBox => {
    if (captionsEnabled) {
      sectionBox.classList.remove("no-captions");
    } else {
      sectionBox.classList.add("no-captions");
    }

    const button = sectionBox.querySelector(".caption-toggle-btn");
    if (!button) return;
    updateCaptionTooltip(sectionBox);

    button.addEventListener("click", function () {
      const isNowHidden = sectionBox.classList.toggle("no-captions");

      // Save global state
      saveCaptionsEnabled(!isNowHidden);

      // Apply to ALL sections so they stay in sync
      sections.forEach(sec => {
        if (isNowHidden) {
          sec.classList.add("no-captions");
        } else {
          sec.classList.remove("no-captions");
        }
        updateCaptionTooltip(sec);
      });
    });
  });

});
