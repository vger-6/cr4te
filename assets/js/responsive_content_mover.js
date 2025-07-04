document.addEventListener('DOMContentLoaded', () => {
  const mobileBreakpoint = window.utils.getBreakpointPx('--mobile-breakpoint') || 768;
  const originalPlaceholders = document.querySelectorAll('.original-placeholder');

  const state = []; // Track what to move

  originalPlaceholders.forEach(original => {
    const targetId = original.getAttribute('data-mobile-target');
    const mobile = document.querySelector(`.mobile-placeholder[data-mobile-target="${targetId}"]`);
    if (!mobile) {
      console.warn(`Missing .mobile-placeholder for target ${targetId}`);
      return;
    }
    const contents = Array.from(original.children);
    if (contents.length === 0) {
      console.warn(`No content inside .original-placeholder with target ${targetId}`);
      return;
    }
    state.push({ contents, original, mobile });
  });

  function updateLayout() {
    const isMobile = window.innerWidth <= mobileBreakpoint;
    state.forEach(({ contents, original, mobile }) => {
      const target = isMobile ? mobile : original;

      // Move content
      contents.forEach(node => {
        if (node.parentElement !== target) {
          target.appendChild(node);
        }
      });

      // Update placeholder visibility
      original.style.display = isMobile ? 'none' : 'block';
      mobile.style.display = isMobile ? 'block' : 'none';
    });
  }

  updateLayout();
  
  let resizeTimeout;
  window.addEventListener('resize', () => {
    clearTimeout(resizeTimeout);
    resizeTimeout = setTimeout(updateLayout, 100);
  });
});

