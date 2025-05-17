function rebuildPaginatedGallery(gallery, pageSize = 20) {
  const allWrappers = Array.from(gallery.querySelectorAll('.image-wrapper'));
  const controls = gallery.parentElement.querySelector('.pagination-controls');

  if (allWrappers.length === 0) return;

  let currentPage = 1;
  const totalPages = Math.ceil(allWrappers.length / pageSize);

  function layoutVisibleImages(visibleWrappers) {
    const galleryBody = document.createElement('div');
    galleryBody.classList.add('image-page');
    gallery.innerHTML = ''; // Clear previous

    galleryBody.style.display = 'flex';
    galleryBody.style.flexDirection = 'column';
    galleryBody.style.gap = '1rem';

    gallery.appendChild(galleryBody);

    const galleryWidth = gallery.clientWidth;

    // Compute how many images can reasonably fit per row based on ideal image width
    const idealImageWidth = 180; // px
    const gap = 16;
    const maxPerRow = 5;

    let imagesPerRow = Math.floor((galleryWidth + gap) / (idealImageWidth + gap));

    // Clamp the result between 1 and maxPerRow
    imagesPerRow = Math.max(1, Math.min(imagesPerRow, maxPerRow));

    for (let i = 0; i < visibleWrappers.length; i += imagesPerRow) {
      const row = document.createElement('div');
      row.classList.add('image-row');

      const rowItems = visibleWrappers.slice(i, i + imagesPerRow);
      rowItems.forEach(w => row.appendChild(w));
      galleryBody.appendChild(row);
    }

    const loadPromises = visibleWrappers.map(wrapper => {
      const img = wrapper.querySelector('img');
      return img.complete ? Promise.resolve() : new Promise(res => img.onload = res);
    });

    Promise.all(loadPromises).then(() => {
      galleryBody.querySelectorAll('.image-row').forEach(row => {
        const wrappers = Array.from(row.querySelectorAll('.image-wrapper'));
        const ratios = wrappers.map(w => {
          const img = w.querySelector('img');
          return img.naturalWidth / img.naturalHeight;
        });

        const totalRatio = ratios.reduce((a, b) => a + b, 0);
        const totalGap = gap * (wrappers.length - 1);
        const rowWidth = row.clientWidth - totalGap;
        const commonHeight = rowWidth / totalRatio;

        wrappers.forEach((wrapper, idx) => {
          const width = commonHeight * ratios[idx];
          wrapper.style.width = `${width}px`;
          wrapper.style.height = `${commonHeight}px`;
        });
      });
    });
  }

  function renderPage(page) {
    const start = (page - 1) * pageSize;
    const end = start + pageSize;
    const visibleWrappers = allWrappers.slice(start, end);
    layoutVisibleImages(visibleWrappers);
    
    // Ensure lightbox bindings update on new pagination page
    rebindLightbox?.();

    if (controls) {
      controls.innerHTML = '';

      // Hide pagination if only one page
      if (totalPages <= 1) {
        controls.style.display = 'none';
        return;
      } else {
        controls.style.display = '';
      }

      for (let i = 1; i <= totalPages; i++) {
        const btn = document.createElement('button');
        btn.textContent = i;
        if (i === page) {
          btn.classList.add('active');
        } else {
          btn.addEventListener('click', () => {
            currentPage = i;
            renderPage(currentPage);
          });
        }
        controls.appendChild(btn);
      }
    }
  }

  renderPage(currentPage);
}

function rebuildAllImageGalleries() {
  document.querySelectorAll('.paginated-gallery').forEach(gallery => {
    const pageSize = parseInt(gallery.dataset.pageSize, 10) || 20;
    rebuildPaginatedGallery(gallery, pageSize);
  });
}

window.addEventListener('DOMContentLoaded', rebuildAllImageGalleries);
window.addEventListener('resize', rebuildAllImageGalleries);

