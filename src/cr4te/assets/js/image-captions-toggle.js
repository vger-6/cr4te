document.addEventListener("DOMContentLoaded", function () {

  const STORAGE_KEY = "imageCaptionsEnabled";
  const sections = document.querySelectorAll(".image-caption-section");
  if (!sections.length) return;

  // Restore state
  const captionsEnabled = localStorage.getItem(STORAGE_KEY) === "true";

  sections.forEach(sectionBox => {
    if (captionsEnabled) {
      sectionBox.classList.remove("no-captions");
    } else {
      sectionBox.classList.add("no-captions");
    }

    const button = sectionBox.querySelector(".caption-toggle-btn");
    if (!button) return;

    button.addEventListener("click", function () {
      const isNowHidden = sectionBox.classList.toggle("no-captions");

      // Save global state
      localStorage.setItem(STORAGE_KEY, !isNowHidden);

      // Apply to ALL sections so they stay in sync
      sections.forEach(sec => {
        if (isNowHidden) {
          sec.classList.add("no-captions");
        } else {
          sec.classList.remove("no-captions");
        }
      });
    });
  });

});
