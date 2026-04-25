function rebuildJustifiedImageGallery() {
  document.querySelectorAll('.image-gallery--justified').forEach(gallery => {
    const maxHeight = parseFloat(gallery.dataset.imageMaxHeight) || 200;

    const computedStyle = window.getComputedStyle(gallery);
    const gap = window.utils.parseCssLength(
      computedStyle.columnGap || computedStyle.gap || "1rem"
    );

    const galleryWidth = gallery.clientWidth;
    if (!galleryWidth) return;

    const allWrappers = Array.from(gallery.querySelectorAll('.image-wrapper'));

    // --- Build items synchronously using dataset ratios ---
    const items = allWrappers.map(wrapper => {
      const img = wrapper.querySelector('img');

      const w = parseFloat(wrapper.dataset.width);
      const h = parseFloat(wrapper.dataset.height);

      const ratio = (w && h) ? (w / h) : 1;

      return { wrapper, img, ratio };
    });

    // --- Clear gallery before rebuilding ---
    gallery.innerHTML = '';

    const rows = [];
    let row = [];
    let totalRatio = 0;

    for (let i = 0; i < items.length; i++) {
      const item = items[i];

      row.push(item);
      totalRatio += item.ratio;

      const totalGap = gap * (row.length - 1);
      const rowHeight = (galleryWidth - totalGap) / totalRatio;

      if (rowHeight <= maxHeight) {
        rows.push([...row]);
        row = [];
        totalRatio = 0;
      }
    }

    // --- Handle last row (pad if needed like before) ---
    if (row.length > 0) {
      let paddedRow = [...row];
      let ratioSum = totalRatio;

      const lastItem = row[row.length - 1];

      while (true) {
        const totalGap = gap * (paddedRow.length - 1);
        const rowHeight = (galleryWidth - totalGap) / ratioSum;

        if (rowHeight <= maxHeight) break;

        paddedRow.push({
          wrapper: null,
          img: null,
          ratio: lastItem.ratio,
          isVirtual: true
        });

        ratioSum += lastItem.ratio;
      }

      rows.push(paddedRow);
    }

    // --- Render rows ---
    rows.forEach(row => {
      const rowEl = document.createElement('div');
      rowEl.classList.add('image-row');
      gallery.appendChild(rowEl);

      const totalRatio = row.reduce((sum, item) => sum + item.ratio, 0);
      const totalGap = gap * (row.length - 1);
      const rowHeight = (galleryWidth - totalGap) / totalRatio;

      row.forEach(item => {
        const width = item.ratio * rowHeight;

        if (item.wrapper && !item.isVirtual) {
          item.wrapper.style.width = `${width}px`;

          if (item.img) {
            item.img.style.height = `${rowHeight}px`;
          }

          rowEl.appendChild(item.wrapper);
        }
      });
    });
  });
}

// --- Init earlier (no need to wait for full load anymore) ---
window.addEventListener('DOMContentLoaded', rebuildJustifiedImageGallery);

// --- Resize (with simple debounce for performance) ---
let resizeTimeout;
window.addEventListener('resize', () => {
  clearTimeout(resizeTimeout);
  resizeTimeout = setTimeout(() => {
    rebuildJustifiedImageGallery();
  }, 100);
});
