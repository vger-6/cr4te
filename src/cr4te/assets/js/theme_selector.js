const THEME_KEY = "cr4te_theme";
const cr4te = window.cr4te = window.cr4te || {};
cr4te.lightbox = cr4te.lightbox || {};

function getThemeClasses() {
  return [...document.querySelectorAll(".theme-option")]
    .map(el => el.dataset.theme)
    .filter(Boolean);
}

function applyTheme(theme) {
  const themeClasses = getThemeClasses();
  const defaultTheme = document.body.dataset.defaultTheme;
  const selectedTheme = themeClasses.includes(theme) ? theme : defaultTheme;

  document.body.classList.remove(...themeClasses);
  if (selectedTheme) {
    document.body.classList.add(selectedTheme);
  }

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
  const savedTheme = loadSavedTheme() || document.body.dataset.defaultTheme;
  applyTheme(savedTheme);

  const toggle = document.getElementById("theme-toggle");
  const panel = document.getElementById("theme-panel");
  const options = [...panel.querySelectorAll(".theme-option")];

  function isOpen() {
    return toggle.getAttribute("aria-expanded") === "true";
  }

  function focusOption(index) {
    if (!options.length) return;
    options[(index + options.length) % options.length].focus();
  }

  function selectedIndex() {
    const index = options.findIndex(option => option.getAttribute("aria-checked") === "true");
    return index >= 0 ? index : 0;
  }

  function openMenu(focusIndex = null) {
    panel.style.display = "block";
    toggle.setAttribute("aria-expanded", "true");
    if (focusIndex !== null) {
      focusOption(focusIndex);
    }
  }

  function closeMenu(returnFocus = false) {
    panel.style.display = "none";
    toggle.setAttribute("aria-expanded", "false");
    if (returnFocus) {
      toggle.focus();
    }
  }

  function selectOption(option) {
    const theme = option.dataset.theme;
    if (theme) {
      saveTheme(theme);
      applyTheme(theme);
      refreshThemeSensitiveLayout();
      closeMenu(true);
    }
  }

  toggle.addEventListener("click", () => {
    if (isOpen()) {
      closeMenu();
    } else {
      openMenu();
    }
  });

  toggle.addEventListener("keydown", event => {
    if (event.key === "ArrowDown") {
      event.preventDefault();
      openMenu(selectedIndex());
    } else if (event.key === "ArrowUp") {
      event.preventDefault();
      openMenu(options.length - 1);
    } else if (event.key === "Escape") {
      event.preventDefault();
      closeMenu(true);
    }
  });

  panel.addEventListener("keydown", event => {
    const currentIndex = options.indexOf(document.activeElement);

    if (event.key === "ArrowDown") {
      event.preventDefault();
      focusOption(currentIndex + 1);
    } else if (event.key === "ArrowUp") {
      event.preventDefault();
      focusOption(currentIndex - 1);
    } else if (event.key === "Home") {
      event.preventDefault();
      focusOption(0);
    } else if (event.key === "End") {
      event.preventDefault();
      focusOption(options.length - 1);
    } else if (event.key === "Escape") {
      event.preventDefault();
      closeMenu(true);
    } else if (event.key === "Tab") {
      closeMenu();
    }
  });

  document.addEventListener("click", event => {
    if (!toggle.contains(event.target) && !panel.contains(event.target)) {
      closeMenu();
    }
  });

  options.forEach(option => {
    option.addEventListener("click", () => {
      selectOption(option);
    });
  });
}

cr4te.onReady(() => {
  initThemeDropdown();
  refreshThemeSensitiveLayout();
});

