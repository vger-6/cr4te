function parsePixels(value) {
  return parseFloat(value) || 0;
}

function getVerticalInsets(element) {
  const styles = getComputedStyle(element);
  return (
    parsePixels(styles.paddingTop) +
    parsePixels(styles.paddingBottom) +
    parsePixels(styles.borderTopWidth) +
    parsePixels(styles.borderBottomWidth)
  );
}

function getPreviousSiblingGap(element) {
  const previous = element.previousElementSibling;
  if (!previous) return 0;

  const previousRect = previous.getBoundingClientRect();
  const elementRect = element.getBoundingClientRect();
  return Math.max(0, elementRect.top - previousRect.bottom);
}

function resizeIframes() {
  const leftColumn = document.querySelector('.left-column');
  const rightColumn = document.querySelector('.right-column');
  const iframes = document.querySelectorAll('.auto-height-iframe');

  if (!rightColumn || iframes.length === 0) return;

  const referenceColumn =
    leftColumn &&
    getComputedStyle(leftColumn).display !== 'none' &&
    leftColumn.getBoundingClientRect().height > 0
      ? leftColumn
      : rightColumn;

  const referenceHeight = referenceColumn.getBoundingClientRect().height;

  iframes.forEach(iframe => {
    const sectionBox = iframe.closest('.section-box');
    if (!sectionBox) return;

    const sectionColumn = iframe.closest('.right-column') || rightColumn;
    const sectionHeight = sectionBox.getBoundingClientRect().height;
    const iframeHeight = iframe.getBoundingClientRect().height;
    const sectionChromeHeight = Math.max(0, sectionHeight - iframeHeight);
    const columnInsetsHeight = getVerticalInsets(sectionColumn);
    const sectionGapBefore = getPreviousSiblingGap(sectionBox);
    const usedVerticalSpace =
      sectionChromeHeight +
      columnInsetsHeight +
      sectionGapBefore;
    const finalHeight = Math.max(0, referenceHeight - usedVerticalSpace);

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
