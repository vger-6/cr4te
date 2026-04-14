function rebuildAspectImageGallery() {
  document.querySelectorAll('.image-gallery--aspect').forEach(gallery => {
    const aspectRatio = gallery.dataset.aspectRatio || "1/1";
    const [w, h] = aspectRatio.split('/').map(Number);
    const maxHeight = parseFloat(gallery.dataset.imageMaxHeight || "200");
    const computedStyle = window.getComputedStyle(gallery);
    const gap = window.utils.parseCssLength(computedStyle.columnGap || computedStyle.gap || "1rem");

    const galleryWidth = gallery.clientWidth;

    // Calculate optimal number of columns so that height doesn't exceed maxHeight
    let columns = 1;
    let found = false;
    while (!found) {
      const totalGap = gap * (columns - 1);
      const availableWidth = galleryWidth - totalGap;
      const itemWidth = availableWidth / columns;
      const itemHeight = itemWidth * (h / w);
      if (itemHeight <= maxHeight) {
        found = true;
      } else {
        columns++;
      }
    }

    // Set CSS grid properties
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

window.addEventListener('DOMContentLoaded', rebuildAspectImageGallery);
window.addEventListener('resize', rebuildAspectImageGallery);

