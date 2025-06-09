let IMAGES_PER_PAGE = 20;
let currentPage = 1;
let allWrappers = [];

function renderPage(page) {
  const gallery = document.getElementById('imageGallery');
  const galleries = document.querySelectorAll('.image-gallery');
  galleries.forEach(initGallery);
}

function initGallery(gallery) {
  const controls = document.createElement('div');
  controls.className = 'pagination-controls';
  gallery.parentElement.appendChild(controls);

  let currentPage = 1;
  let IMAGES_PER_PAGE = parseInt(gallery.dataset.pageSize) || 20;
  const allWrappers = Array.from(gallery.querySelectorAll('.image-wrapper'));

  function renderPage(page) {
    const start = (page - 1) * IMAGES_PER_PAGE;
    const end = start + IMAGES_PER_PAGE;
    const visibleWrappers = allWrappers.slice(start, end);

    gallery.innerHTML = '';
    visibleWrappers.forEach(wrapper => gallery.appendChild(wrapper));
    rebuildImageGallery?.();

    const totalPages = Math.ceil(allWrappers.length / IMAGES_PER_PAGE);
    controls.innerHTML = '';

    if (totalPages > 1) {
      for (let i = 1; i <= totalPages; i++) {
        const btn = document.createElement('button');
        btn.textContent = i;
        if (i === page) btn.classList.add('active');
        btn.onclick = () => {
          currentPage = i;
          renderPage(currentPage);
          rebindLightbox?.();
        };
        controls.appendChild(btn);
      }
    } else {
      controls.style.display = 'none';
    }
  }

  renderPage(currentPage);
  window.addEventListener('resize', () => renderPage(currentPage));
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

