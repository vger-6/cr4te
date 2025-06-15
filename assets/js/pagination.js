let IMAGES_PER_PAGE_DEFAULT = 20;

// TODO: break setupPagination into:
// function renderPaginationControls(gallery, currentPage, totalPages, onPageClick)
// function paginateWrappers(wrappers, pageSize, currentPage)
function setupPagination(gallery, allWrappers, pageSize = IMAGES_PER_PAGE_DEFAULT) {
  let controls = gallery.parentElement.querySelector('.pagination-controls');
  if (!controls) {
    controls = document.createElement('div');
    controls.className = 'pagination-controls';
    gallery.parentElement.appendChild(controls);
  } else {
    controls.style.display = ''; // un-hide if it was hidden previously
  }

  let currentPage = 1;

  function renderPage(page) {
    const start = (page - 1) * pageSize;
    const end = start + pageSize;
    const visibleWrappers = allWrappers.slice(start, end);

    gallery.innerHTML = '';
    visibleWrappers.forEach(wrapper => gallery.appendChild(wrapper));

    rebuildImageGallery?.();
    if (typeof rebindLightbox === 'function') rebindLightbox();

    const totalPages = Math.ceil(allWrappers.length / pageSize);
    controls.innerHTML = '';

    if (totalPages > 1) {
      for (let i = 1; i <= totalPages; i++) {
        const btn = document.createElement('button');
        btn.textContent = i;
        if (i === page) btn.classList.add('active');
        btn.onclick = () => {
          currentPage = i;
          renderPage(currentPage);
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

window.paginateGallery = setupPagination;

// Auto-run pagination on pages without a search bar
document.addEventListener('DOMContentLoaded', () => {
  document.querySelectorAll('.image-gallery').forEach(gallery => {
    const hasSearch = !!document.getElementById('search-input');
    if (hasSearch && gallery.id === 'imageGallery') return; // skip; filtered separately

    const wrappers = Array.from(gallery.querySelectorAll('.image-wrapper'));
    const pageSize = parseInt(gallery.dataset.pageSize) || IMAGES_PER_PAGE_DEFAULT;
    setupPagination(gallery, wrappers, pageSize);
  });
});

