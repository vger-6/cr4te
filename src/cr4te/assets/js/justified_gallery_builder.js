(function () {
  const cr4te = window.cr4te = window.cr4te || {};
  cr4te.galleries = cr4te.galleries || {};

  function ratioForWrapper(wrapper) {
    const w = parseFloat(wrapper.dataset.width);
    const h = parseFloat(wrapper.dataset.height);
    return (w && h) ? (w / h) : 1;
  }

  function buildRows(items, galleryWidth, gap, maxHeight) {
    const rows = [];
    let row = [];
    let totalRatio = 0;

    items.forEach(item => {
      row.push(item);
      totalRatio += item.ratio;

      const totalGap = gap * (row.length - 1);
      const rowHeight = (galleryWidth - totalGap) / totalRatio;

      if (rowHeight <= maxHeight) {
        rows.push([...row]);
        row = [];
        totalRatio = 0;
      }
    });

    if (row.length > 0) {
      rows.push(padLastRow(row, totalRatio, galleryWidth, gap, maxHeight));
    }

    return rows;
  }

  function padLastRow(row, totalRatio, galleryWidth, gap, maxHeight) {
    const paddedRow = [...row];
    const lastItem = row[row.length - 1];
    let ratioSum = totalRatio;

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

    return paddedRow;
  }

  function renderRows(gallery, rows, galleryWidth, gap) {
    gallery.innerHTML = '';

    rows.forEach(row => {
      const rowEl = document.createElement('div');
      rowEl.classList.add('image-row');
      gallery.appendChild(rowEl);

      const totalRatio = row.reduce((sum, item) => sum + item.ratio, 0);
      const totalGap = gap * (row.length - 1);
      const rowHeight = (galleryWidth - totalGap) / totalRatio;

      row.forEach(item => {
        if (!item.wrapper || item.isVirtual) return;

        const width = item.ratio * rowHeight;
        item.wrapper.style.width = `${width}px`;

        if (item.img) {
          item.img.style.height = `${rowHeight}px`;
        }

        rowEl.appendChild(item.wrapper);
      });
    });
  }

  function getJustifiedGalleries(root = document) {
    const searchRoot = root?.querySelectorAll ? root : document;
    const galleries = Array.from(searchRoot.querySelectorAll('.image-gallery--justified'));

    if (searchRoot.matches?.('.image-gallery--justified')) {
      galleries.unshift(searchRoot);
    }

    return galleries;
  }

  function rebuildJustifiedImageGallery(root = document) {
    getJustifiedGalleries(root).forEach(gallery => {
      const maxHeight = parseFloat(gallery.dataset.imageMaxHeight) || 200;
      const computedStyle = window.getComputedStyle(gallery);
      const gap = window.utils.parseCssLength(
        computedStyle.columnGap || computedStyle.gap || "1rem"
      );
      const galleryWidth = gallery.clientWidth;

      if (!galleryWidth) return;

      const items = Array.from(gallery.querySelectorAll('.image-wrapper')).map(wrapper => ({
        wrapper,
        img: wrapper.querySelector('img'),
        ratio: ratioForWrapper(wrapper),
      }));

      renderRows(gallery, buildRows(items, galleryWidth, gap, maxHeight), galleryWidth, gap);
    });
  }

  cr4te.galleries.rebuildJustified = rebuildJustifiedImageGallery;

  cr4te.onReady(rebuildJustifiedImageGallery);

  let resizeTimeout;
  window.addEventListener('resize', () => {
    clearTimeout(resizeTimeout);
    resizeTimeout = setTimeout(rebuildJustifiedImageGallery, 100);
  });
})();
