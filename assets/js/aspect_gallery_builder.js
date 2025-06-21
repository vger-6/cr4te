function rebuildAspectImageGallery() {
  document.querySelectorAll('.image-gallery--aspect').forEach(gallery => {
    const aspectRatio = gallery.dataset.aspectRatio || "1/1";
    const [w, h] = aspectRatio.split('/').map(Number);
    const maxHeight = parseFloat(gallery.dataset.imageMaxHeight || "200"); // fallback 200px

    const maxWidth = Math.floor(maxHeight * (w / h));
    gallery.style.gridTemplateColumns = `repeat(auto-fill, minmax(${maxWidth}px, 1fr))`;

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

