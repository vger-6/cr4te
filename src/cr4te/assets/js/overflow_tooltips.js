(function () {
  window.cr4te.overflowTooltips = window.cr4te.overflowTooltips || {};

  const SELECTOR = [
    ".breadcrumb-section [data-overflow-title]",
    ".section-title",
    ".tag-category-label",
    ".tag",
    ".track-title-text",
    ".image-caption",
    ".creator-text-card__name",
    ".creator-text-card__summary",
  ].join(", ");
  const OVERFLOW_TOLERANCE = 1;

  function sectionTitleTextElement(element) {
    const firstChild = element.firstElementChild;

    return firstChild && firstChild.tagName === "SPAN" ? firstChild : null;
  }

  function measuredElement(element) {
    if (element.classList.contains("section-title")) {
      return sectionTitleTextElement(element) || element;
    }

    return element;
  }

  function normalizedText(text) {
    return text.replace(/\s+/g, " ").trim();
  }

  function tooltipText(element, measured) {
    return element.dataset.overflowTitle || normalizedText(measured.textContent);
  }

  function isOverflowing(element) {
    const measured = measuredElement(element);
    const hasHorizontalOverflow = measured.scrollWidth > measured.clientWidth + OVERFLOW_TOLERANCE;
    const hasVerticalOverflow = measured.scrollHeight > measured.clientHeight + OVERFLOW_TOLERANCE;

    return hasHorizontalOverflow || hasVerticalOverflow;
  }

  function updateTooltip(element) {
    const measured = measuredElement(element);
    const title = tooltipText(element, measured);

    if (title && isOverflowing(element)) {
      measured.setAttribute("title", title);
      return;
    }

    measured.removeAttribute("title");
  }

  function updateTooltips() {
    document.querySelectorAll(SELECTOR).forEach(updateTooltip);
  }

  function initOverflowTooltips() {
    const items = document.querySelectorAll(SELECTOR);

    if (!items.length) return;

    window.cr4te.overflowTooltips.update = updateTooltips;

    updateTooltips();
    window.addEventListener("resize", updateTooltips);

    if ("ResizeObserver" in window) {
      const observer = new ResizeObserver(updateTooltips);
      items.forEach(item => {
        observer.observe(item);

        const measured = measuredElement(item);
        if (measured !== item) {
          observer.observe(measured);
        }
      });
      document.querySelectorAll(".breadcrumb-section").forEach(section => observer.observe(section));
      window.cr4te.overflowTooltips.resizeObserver = observer;
    }

    if (document.fonts && document.fonts.ready) {
      document.fonts.ready.then(updateTooltips);
    }
  }

  window.cr4te.onReady(initOverflowTooltips);
})();
