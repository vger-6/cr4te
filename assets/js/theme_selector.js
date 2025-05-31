const THEME_KEY = "cr4te_theme";
const DEFAULT_THEME = "theme-frozen-aurora";

function applyTheme(theme) {
  document.body.classList.remove(...document.body.classList);
  document.body.classList.add(theme);

  // Highlight selected option
  document.querySelectorAll('.theme-option').forEach(el => {
    el.classList.toggle('selected', el.dataset.theme === theme);
  });
  
  document.body.style.display = "block";
}

function initThemeDropdown() {
  const savedTheme = localStorage.getItem(THEME_KEY) || DEFAULT_THEME;
  applyTheme(savedTheme);

  // Toggle panel visibility
  const toggle = document.getElementById("theme-toggle");
  const panel = document.getElementById("theme-panel");

  toggle.addEventListener("click", () => {
    panel.style.display = panel.style.display === "block" ? "none" : "block";
  });

  // Hide panel on outside click
  document.addEventListener("click", (e) => {
    if (!toggle.contains(e.target) && !panel.contains(e.target)) {
      panel.style.display = "none";
    }
  });

  // Handle theme selection
  document.querySelectorAll(".theme-option").forEach(opt => {
    opt.addEventListener("click", () => {
      const theme = opt.dataset.theme;
      localStorage.setItem(THEME_KEY, theme);
      applyTheme(theme);
      panel.style.display = "none";
    });
  });
}

document.addEventListener("DOMContentLoaded", initThemeDropdown);

