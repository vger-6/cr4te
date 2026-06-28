(function () {
  window.cr4te.breadcrumbTooltips = window.cr4te.breadcrumbTooltips || {};

  const SELECTOR = ".breadcrumb-section [data-overflow-title]";
  const OVERFLOW_TOLERANCE = 1;

  function isOverflowing(element) {
    return element.scrollWidth > element.clientWidth + OVERFLOW_TOLERANCE;
  }

  function updateTooltip(element) {
    const title = element.dataset.overflowTitle || element.textContent.trim();

    if (isOverflowing(element)) {
      element.setAttribute("title", title);
      return;
    }

    element.removeAttribute("title");
  }

  function updateTooltips() {
    document.querySelectorAll(SELECTOR).forEach(updateTooltip);
  }

  function initBreadcrumbTooltips() {
    const items = document.querySelectorAll(SELECTOR);

    if (!items.length) return;

    window.cr4te.breadcrumbTooltips.update = updateTooltips;

    updateTooltips();
    window.addEventListener("resize", updateTooltips);

    if ("ResizeObserver" in window) {
      const observer = new ResizeObserver(updateTooltips);
      items.forEach(item => observer.observe(item));
      document.querySelectorAll(".breadcrumb-section").forEach(section => observer.observe(section));
      window.cr4te.breadcrumbTooltips.resizeObserver = observer;
    }

    if (document.fonts && document.fonts.ready) {
      document.fonts.ready.then(updateTooltips);
    }
  }

  window.cr4te.onReady(initBreadcrumbTooltips);
})();
