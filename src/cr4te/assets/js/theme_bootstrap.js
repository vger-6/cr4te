(function () {
  const root = document.documentElement;
  const themes = (root.dataset.themeClasses || "").split(/\s+/).filter(Boolean);
  const defaultTheme = root.dataset.defaultTheme || themes[0] || "";
  let selectedTheme = defaultTheme;

  root.classList.add("cr4te-js");

  try {
    const savedTheme = localStorage.getItem("cr4te_theme");
    if (themes.includes(savedTheme)) {
      selectedTheme = savedTheme;
    }
  } catch {
    selectedTheme = defaultTheme;
  }

  if (!selectedTheme) return;

  root.classList.remove(...themes);
  root.classList.add(selectedTheme);
  root.dataset.resolvedTheme = selectedTheme;
})();
