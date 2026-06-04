const THEME_KEY = "cr4te_theme";
const DEFAULT_THEME = "theme-frozen-aurora";
const cr4te = window.cr4te = window.cr4te || {};
cr4te.lightbox = cr4te.lightbox || {};

function getThemeClasses() {
  return [...document.querySelectorAll(".theme-option")]
    .map(el => el.dataset.theme)
    .filter(Boolean);
}

function applyTheme(theme) {
  const themeClasses = getThemeClasses();
  const selectedTheme = themeClasses.includes(theme) ? theme : DEFAULT_THEME;

  document.body.classList.remove(...themeClasses);
  document.body.classList.add(selectedTheme);

  // Highlight selected option
  document.querySelectorAll('.theme-option').forEach(el => {
    el.classList.toggle('selected', el.dataset.theme === selectedTheme);
  });
  
  document.body.style.display = "block";
}

function refreshThemeSensitiveLayout() {
  requestAnimationFrame(() => {
    requestAnimationFrame(() => {
      window.dispatchEvent(new Event("resize"));
      cr4te.lightbox.rebind?.();
      cr4te.lightbox.rebindSingle?.();
    });
  });
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
      refreshThemeSensitiveLayout();
      panel.style.display = "none";
    });
  });
}

cr4te.onReady(() => {
  initThemeDropdown();
  refreshThemeSensitiveLayout();
});

