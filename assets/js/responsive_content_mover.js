document.addEventListener("DOMContentLoaded", function() {
  const mobileBreakpoint = window.utils.getBreakpointPx();
  const sections = document.querySelectorAll('.moveable-to-placeholder');
  const mobilePlaceholder = document.getElementById('placeholder');

  if (!mobilePlaceholder) return;

  function relocateSections() {
    if (window.innerWidth <= mobileBreakpoint) {
      sections.forEach(el => mobilePlaceholder.appendChild(el));
    } else {
      sections.forEach(el => {
        const placeholderId = el.dataset.placeholderId;
        const originalPlaceholder = document.getElementById(placeholderId);
        if (originalPlaceholder) {
          originalPlaceholder.insertAdjacentElement('afterend', el);
        }
      });
    }
  }

  relocateSections();
  let resizeTimeout;
  window.addEventListener('resize', () => {
    clearTimeout(resizeTimeout);
    resizeTimeout = setTimeout(relocateSections, 100);
  });
});

