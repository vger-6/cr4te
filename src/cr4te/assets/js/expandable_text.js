(function () {
  window.cr4te.expandableText = window.cr4te.expandableText || {};

  const SELECTOR = "[data-expandable-text]";
  const OVERFLOW_TOLERANCE = 1;

  function contentElement(root) {
    return root.querySelector("[data-expandable-text-content]");
  }

  function toggleButton(root) {
    return root.querySelector("[data-expandable-text-toggle]");
  }

  function setToggleLabel(button, expanded) {
    button.textContent = expanded ? button.dataset.showLessLabel : button.dataset.showMoreLabel;
  }

  function setExpanded(root, expanded) {
    const button = toggleButton(root);

    root.classList.toggle("is-expanded", expanded);
    root.classList.toggle("is-collapsed", !expanded);
    button.setAttribute("aria-expanded", expanded ? "true" : "false");
    setToggleLabel(button, expanded);
  }

  function isOverflowingWhenCollapsed(root) {
    const content = contentElement(root);
    const wasCollapsible = root.classList.contains("is-collapsible");
    const wasExpanded = root.classList.contains("is-expanded");
    const wasCollapsed = root.classList.contains("is-collapsed");

    root.classList.add("is-collapsible");
    root.classList.add("is-collapsed");
    root.classList.remove("is-expanded");

    const isOverflowing = content.scrollHeight > content.clientHeight + OVERFLOW_TOLERANCE;

    root.classList.toggle("is-collapsible", wasCollapsible);
    root.classList.toggle("is-expanded", wasExpanded);
    root.classList.toggle("is-collapsed", wasCollapsed);

    return isOverflowing;
  }

  function updateExpandableText(root) {
    const content = contentElement(root);
    const button = toggleButton(root);

    if (!content || !button) return;

    const isCollapsible = isOverflowingWhenCollapsed(root);

    root.classList.toggle("is-collapsible", isCollapsible);
    button.hidden = !isCollapsible;

    if (!isCollapsible) {
      root.classList.remove("is-collapsed", "is-expanded");
      button.setAttribute("aria-expanded", "false");
      setToggleLabel(button, false);
      return;
    }

    setExpanded(root, root.classList.contains("is-expanded"));
  }

  function updateAllExpandableText() {
    document.querySelectorAll(SELECTOR).forEach(updateExpandableText);
  }

  function initExpandableText() {
    const roots = document.querySelectorAll(SELECTOR);

    if (!roots.length) return;

    roots.forEach(root => {
      const button = toggleButton(root);

      if (!button) return;

      button.addEventListener("click", () => {
        setExpanded(root, !root.classList.contains("is-expanded"));
      });
    });

    window.cr4te.expandableText.update = updateAllExpandableText;

    updateAllExpandableText();
    window.addEventListener("resize", updateAllExpandableText);

    if ("ResizeObserver" in window) {
      const observer = new ResizeObserver(updateAllExpandableText);
      roots.forEach(root => {
        observer.observe(root);

        const content = contentElement(root);
        if (content) {
          observer.observe(content);
        }
      });
      window.cr4te.expandableText.resizeObserver = observer;
    }

    if (document.fonts && document.fonts.ready) {
      document.fonts.ready.then(updateAllExpandableText);
    }
  }

  window.cr4te.onReady(initExpandableText);
})();
