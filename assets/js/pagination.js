(function () {
  let IMAGES_PER_PAGE_DEFAULT = 20;

  // TODO: break setupPagination into:
  // function renderPaginationControls(gallery, currentPage, totalPages, onPageClick)
  // function paginateWrappers(wrappers, pageSize, currentPage)
  function setupPagination(gallery, allWrappers, pageSize = IMAGES_PER_PAGE_DEFAULT) {
    let wrapper = gallery.parentElement.querySelector('.pagination-controls-wrapper'); // sticky background
    let controls = wrapper ? wrapper.querySelector('.pagination-controls') : null;

    if (!controls) {
      wrapper = document.createElement('div');
      wrapper.className = 'pagination-controls-wrapper';

      controls = document.createElement('div');
      controls.className = 'pagination-controls';

      wrapper.appendChild(controls);
      gallery.parentElement.appendChild(wrapper);
    } else {
      wrapper.style.display = ''; // un-hide the whole wrapper (NOT just the controls)
    }

    let currentPage = 1;
    
    function getExplicitScrollableAncestor(el) {
      let parent = el.parentElement;
      while (parent) {
        const style = window.getComputedStyle(parent);
        const overflowY = style.getPropertyValue('overflow-y');
        const isScrollable = (overflowY === 'auto' || overflowY === 'scroll');
        const canScroll = parent.scrollHeight > parent.clientHeight;

        if (isScrollable && canScroll) {
          return parent;
        }

        parent = parent.parentElement;
      }
      return null;
    }

    function renderPage(page, autoScroll = false) {
      const start = (page - 1) * pageSize;
      const end = start + pageSize;
      const visibleWrappers = allWrappers.slice(start, end);

      gallery.innerHTML = '';
      visibleWrappers.forEach(wrapper => gallery.appendChild(wrapper));

      if (typeof rebuildJustifiedImageGallery === 'function') rebuildJustifiedImageGallery();
      if (typeof rebuildAspectImageGallery === 'function') rebuildAspectImageGallery();
      if (typeof rebindLightbox === 'function') rebindLightbox();

      const totalPages = Math.ceil(allWrappers.length / pageSize);
      controls.innerHTML = '';

      if (totalPages > 1) {
        for (let i = 1; i <= totalPages; i++) {
          const btn = document.createElement('button');
          btn.textContent = i;
          if (i === page) {
            btn.classList.add('in-active');
          }
          else {
            btn.onclick = () => {
              currentPage = i;
              renderPage(currentPage, true);
            };
          }
          controls.appendChild(btn);
        }
      } else {
        wrapper.style.display = 'none'; // hide if only 1 page
      }

      // Scroll section-box containing the gallery into view after page change
      if (autoScroll) {
        const sectionBox = gallery.closest('.section-box');
        if (sectionBox) {
          const scrollContainer = getExplicitScrollableAncestor(sectionBox);

          requestAnimationFrame(() => {
            // This runs after the browser has done a reflow/layout pass
            if (scrollContainer) {
              scrollContainer.scrollTo({
                top: sectionBox.offsetTop - scrollContainer.offsetTop,
                behavior: 'smooth'
              });
            } 
          });
        }
      }
    }

    renderPage(currentPage);
    window.addEventListener('resize', () => renderPage(currentPage));
  }

  window.paginateGallery = setupPagination;

  // Auto-run pagination on pages without a search bar
  document.addEventListener('DOMContentLoaded', () => {
    document.querySelectorAll('.image-gallery--justified, .image-gallery--aspect').forEach(gallery => {
      const hasSearch = !!document.getElementById('search-input');
      if (hasSearch && gallery.id === 'imageGallery') return; // skip; filtered separately

      const wrappers = Array.from(gallery.querySelectorAll('.image-wrapper'));
      const pageSize = parseInt(gallery.dataset.pageSize) || IMAGES_PER_PAGE_DEFAULT;
      setupPagination(gallery, wrappers, pageSize);
    });
  });
})();
