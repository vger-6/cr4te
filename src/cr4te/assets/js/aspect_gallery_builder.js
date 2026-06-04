(function () {
  const cr4te = window.cr4te = window.cr4te || {};
  cr4te.galleries = cr4te.galleries || {};

  function parseAspectRatio(value) {
    const [w, h] = (value || "1/1").split('/').map(Number);
    return w > 0 && h > 0 ? { w, h } : { w: 1, h: 1 };
  }

  function calculateColumns(galleryWidth, gap, maxHeight, w, h) {
    if (!galleryWidth) return 1;

    let columns = 1;
    while (true) {
      const totalGap = gap * (columns - 1);
      const availableWidth = galleryWidth - totalGap;
      const itemWidth = availableWidth / columns;
      const itemHeight = itemWidth * (h / w);

      if (itemHeight <= maxHeight) {
        return columns;
      }

      columns++;
    }
  }

  function getAspectGalleries(root = document) {
    const searchRoot = root?.querySelectorAll ? root : document;
    const galleries = Array.from(searchRoot.querySelectorAll('.image-gallery--aspect'));

    if (searchRoot.matches?.('.image-gallery--aspect')) {
      galleries.unshift(searchRoot);
    }

    return galleries;
  }

  function rebuildAspectImageGallery(root = document) {
    getAspectGalleries(root).forEach(gallery => {
      const { w, h } = parseAspectRatio(gallery.dataset.aspectRatio);
      const maxHeight = parseFloat(gallery.dataset.imageMaxHeight || "200");
      const computedStyle = window.getComputedStyle(gallery);
      const gap = window.utils.parseCssLength(computedStyle.columnGap || computedStyle.gap || "1rem");
      const galleryWidth = gallery.clientWidth;
      const columns = calculateColumns(galleryWidth, gap, maxHeight, w, h);
      const totalGap = gap * (columns - 1);
      const availableWidth = galleryWidth - totalGap;
      const itemWidth = availableWidth / columns;

      gallery.style.gridTemplateColumns = `repeat(${columns}, ${itemWidth}px)`;
      gallery.style.gap = `${gap}px`;

      gallery.querySelectorAll('.image-wrapper').forEach(wrapper => {
        const img = wrapper.querySelector('img');
        if (!img || img.classList.contains('processed-aspect')) return;

        const aspectBox = document.createElement('div');
        aspectBox.classList.add('aspect-ratio-box');
        aspectBox.style.aspectRatio = `${w} / ${h}`;
        img.classList.add('processed-aspect');

        img.parentNode.replaceChild(aspectBox, img);
        aspectBox.appendChild(img);
      });
    });
  }

  cr4te.galleries.rebuildAspect = rebuildAspectImageGallery;

  cr4te.onReady(rebuildAspectImageGallery);
  window.addEventListener('resize', () => rebuildAspectImageGallery());
})();
