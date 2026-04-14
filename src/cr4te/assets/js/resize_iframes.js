function resizeIframes() {
  const rightColumn = document.querySelector('.right-column');
  const iframes = document.querySelectorAll('.auto-height-iframe');

  if (!rightColumn || iframes.length === 0) return;

  const rect = rightColumn.getBoundingClientRect();

  const visibleHeight =
    Math.min(rect.bottom, window.innerHeight) -
    Math.max(rect.top, 0);

  const styles = getComputedStyle(document.body);
  const margin =
    parseFloat(styles.getPropertyValue('--iframe-vertical-margin')) || 0;

  const finalHeight = Math.max(0, visibleHeight - margin);

  iframes.forEach(iframe => {
    iframe.style.height = finalHeight + 'px';
  });
}

window.addEventListener('load', resizeIframes);
window.addEventListener('resize', resizeIframes);

let ticking = false;
window.addEventListener('scroll', () => {
  if (!ticking) {
    requestAnimationFrame(() => {
      resizeIframes();
      ticking = false;
    });
    ticking = true;
  }
});
