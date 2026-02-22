document.addEventListener("DOMContentLoaded", function () {

  const STORAGE_KEY = "imageCaptionsEnabled";
  const sectionBox = document.querySelector(".image-caption-section");
  if (!sectionBox) return;

  // Restore state
  const captionsEnabled = localStorage.getItem(STORAGE_KEY);
  if (captionsEnabled === "true") {
    sectionBox.classList.remove("no-captions");
  } else {
    sectionBox.classList.add("no-captions");
  }

  // Toggle handler
  const button = sectionBox.querySelector(".caption-toggle-btn");
  if (!button) return;

  button.addEventListener("click", function () {
    const isNowHidden = sectionBox.classList.toggle("no-captions");
    localStorage.setItem(STORAGE_KEY, !isNowHidden);
  });

});
