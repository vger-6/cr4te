let IMAGES_PER_PAGE = 20;
let currentPage = 1;
let allWrappers = [];

function renderPage(page) {
  const gallery = document.getElementById('imageGallery');
  const controls = gallery.parentElement.querySelector('.pagination-controls');
  
  const configuredPageSize = parseInt(gallery.dataset.pageSize);
  if (!isNaN(configuredPageSize) && configuredPageSize > 0) {
    IMAGES_PER_PAGE = configuredPageSize;
  }

  const start = (page - 1) * IMAGES_PER_PAGE;
  const end = start + IMAGES_PER_PAGE;
  const visibleWrappers = allWrappers.slice(start, end);

  // Render only visible wrappers
  gallery.innerHTML = '';
  visibleWrappers.forEach(wrapper => gallery.appendChild(wrapper));
  rebuildImageGallery(); // Apply layout and sizing

  // Build pagination controls
  const totalPages = Math.ceil(allWrappers.length / IMAGES_PER_PAGE);
  if (controls) {
    controls.innerHTML = '';

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
          if (typeof rebindLightbox === 'function') {
            rebindLightbox(); // Rebind lightbox to new images
          }
        });
      }
      controls.appendChild(btn);
    }
  }
}

window.addEventListener('DOMContentLoaded', () => {
  const gallery = document.getElementById('imageGallery');
  if (!gallery) return;

  allWrappers = Array.from(gallery.querySelectorAll('.image-wrapper'));
  const paginationContainer = document.createElement('div');
  paginationContainer.className = 'pagination-controls';
  gallery.parentElement.appendChild(paginationContainer);

  renderPage(currentPage);
});

window.addEventListener('resize', () => {
  renderPage(currentPage);
});

