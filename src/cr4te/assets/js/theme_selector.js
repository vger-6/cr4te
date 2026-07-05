const THEME_KEY = "cr4te_theme";
const cr4te = window.cr4te = window.cr4te || {};
cr4te.lightbox = cr4te.lightbox || {};

function getThemeRoot() {
  return document.documentElement;
}

function getThemeClasses() {
  const rootThemes = (getThemeRoot().dataset.themeClasses || "").split(/\s+/).filter(Boolean);
  if (rootThemes.length) return rootThemes;

  return [...document.querySelectorAll(".theme-option")]
    .map(el => el.dataset.theme)
    .filter(Boolean);
}

function applyTheme(theme) {
  const themeClasses = getThemeClasses();
  const defaultTheme = getThemeRoot().dataset.defaultTheme || document.body.dataset.defaultTheme;
  const selectedTheme = themeClasses.includes(theme) ? theme : defaultTheme;

  [getThemeRoot(), document.body].forEach(element => {
    element.classList.remove(...themeClasses);
    if (selectedTheme) {
      element.classList.add(selectedTheme);
    }
  });

  getThemeRoot().dataset.resolvedTheme = selectedTheme;

  // Highlight selected option
  document.querySelectorAll('.theme-option').forEach(el => {
    const isSelected = el.dataset.theme === selectedTheme;
    el.classList.toggle('selected', isSelected);
    el.setAttribute('aria-checked', String(isSelected));
  });
}

function loadSavedTheme() {
  try {
    return localStorage.getItem(THEME_KEY);
  } catch {
    return null;
  }
}

function saveTheme(theme) {
  try {
    localStorage.setItem(THEME_KEY, theme);
  } catch {
    // Theme selection still works for the current page.
  }
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
  const savedTheme = loadSavedTheme() || getThemeRoot().dataset.resolvedTheme || getThemeRoot().dataset.defaultTheme;
  applyTheme(savedTheme);

  const toggle = document.getElementById("theme-toggle");
  const panel = document.getElementById("theme-panel");
  if (!toggle || !panel) return;
  if (typeof cr4te.menus?.bindMenu !== "function") return;

  const options = [...panel.querySelectorAll(".theme-option")];

  function selectedIndex() {
    const index = options.findIndex(option => option.getAttribute("aria-checked") === "true");
    return index >= 0 ? index : 0;
  }

  let menu = null;

  function selectOption(option) {
    const theme = option.dataset.theme;
    if (theme) {
      saveTheme(theme);
      applyTheme(theme);
      refreshThemeSensitiveLayout();
      menu?.close(true);
    }
  }

  menu = cr4te.menus.bindMenu({
    toggle,
    panel,
    options,
    initialFocusIndex: selectedIndex,
    onOptionSelected: selectOption,
  });
}

cr4te.onReady(() => {
  initThemeDropdown();
  refreshThemeSensitiveLayout();
});

