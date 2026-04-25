(function () {
  let IMAGES_PER_PAGE_DEFAULT = 20;

  function setupPagination(gallery, allWrappers, pageSize = IMAGES_PER_PAGE_DEFAULT) {
    let wrapper = gallery.parentElement.querySelector('.pagination-controls-wrapper');
    let controls = wrapper ? wrapper.querySelector('.pagination-controls') : null;

    if (!controls) {
      wrapper = document.createElement('div');
      wrapper.className = 'pagination-controls-wrapper';

      controls = document.createElement('div');
      controls.className = 'pagination-controls';

      wrapper.appendChild(controls);
      gallery.parentElement.appendChild(wrapper);
    } else {
      wrapper.style.display = '';
    }

    let currentPage = 1;

    function getRatio(wrapper) {
      const w = parseFloat(wrapper.dataset.width);
      const h = parseFloat(wrapper.dataset.height);
      if (!w || !h) return 1;
      return w / h;
    }

    function extendToCompleteRow(gallery, allWrappers, slice, nextIndex) {
      if (nextIndex >= allWrappers.length) return slice;

      if (gallery.classList.contains('image-gallery--justified')) {
        return extendJustifiedRow(gallery, allWrappers, slice, nextIndex);
      }

      if (gallery.classList.contains('image-gallery--aspect')) {
        return extendAspectRow(gallery, allWrappers, slice, nextIndex);
      }

      return slice;
    }

    function extendJustifiedRow(gallery, allWrappers, slice, nextIndex) {
      const maxHeight = parseFloat(gallery.dataset.imageMaxHeight) || 200;
      const computedStyle = window.getComputedStyle(gallery);
      const gap = window.utils.parseCssLength(
        computedStyle.columnGap || computedStyle.gap || "1rem"
      );
      const galleryWidth = gallery.clientWidth;

      if (!galleryWidth) return slice;

      let row = [];
      let ratioSum = 0;

      for (let wrapper of slice) {
        const ratio = getRatio(wrapper);

        row.push(ratio);
        ratioSum += ratio;

        const totalGap = gap * (row.length - 1);
        const rowHeight = (galleryWidth - totalGap) / ratioSum;

        if (rowHeight <= maxHeight) {
          row = [];
          ratioSum = 0;
        }
      }

      const initialLength = slice.length;

      while (
        row.length > 0 &&
        nextIndex < allWrappers.length &&
        slice.length < initialLength + 10
      ) {
        const wrapper = allWrappers[nextIndex];
        const ratio = getRatio(wrapper);

        row.push(ratio);
        ratioSum += ratio;
        slice.push(wrapper);
        nextIndex++;

        const totalGap = gap * (row.length - 1);
        const rowHeight = (galleryWidth - totalGap) / ratioSum;

        if (rowHeight <= maxHeight) break;
      }

      return slice;
    }

    function extendAspectRow(gallery, allWrappers, slice, nextIndex) {
      const aspectRatio = gallery.dataset.aspectRatio || "1/1";
      const [w, h] = aspectRatio.split('/').map(Number);

      const computedStyle = window.getComputedStyle(gallery);
      const gap = window.utils.parseCssLength(
        computedStyle.columnGap || computedStyle.gap || "1rem"
      );
      const galleryWidth = gallery.clientWidth;
      const maxHeight = parseFloat(gallery.dataset.imageMaxHeight || "200");

      if (!galleryWidth) return slice;

      let columns = 1;
      while (true) {
        const totalGap = gap * (columns - 1);
        const availableWidth = galleryWidth - totalGap;
        const itemWidth = availableWidth / columns;
        const itemHeight = itemWidth * (h / w);

        if (itemHeight <= maxHeight) break;
        columns++;
      }

      const remainder = slice.length % columns;
      if (remainder === 0) return slice;

      const needed = columns - remainder;

      for (let i = 0; i < needed && nextIndex < allWrappers.length; i++) {
        slice.push(allWrappers[nextIndex]);
        nextIndex++;
      }

      return slice;
    }

    function buildPages() {
      const pages = [];
      let index = 0;

      while (index < allWrappers.length) {
        let slice = allWrappers.slice(index, index + pageSize);

        slice = extendToCompleteRow(
          gallery,
          allWrappers,
          slice,
          index + slice.length
        );

        pages.push(slice);

        index += slice.length;
      }

      return pages;
    }

    let pages = buildPages();

    function renderPage(page, autoScroll = false) {
      const visibleWrappers = pages[page - 1] || [];

      gallery.innerHTML = '';
      visibleWrappers.forEach(wrapper => gallery.appendChild(wrapper));

      if (gallery.classList.contains('image-gallery--justified')) {
        if (typeof rebuildJustifiedImageGallery === 'function') {
          rebuildJustifiedImageGallery();
        }
      } else if (gallery.classList.contains('image-gallery--aspect')) {
        if (typeof rebuildAspectImageGallery === 'function') {
          rebuildAspectImageGallery();
        }
      }

      if (typeof rebindLightbox === 'function') rebindLightbox();

      const totalPages = pages.length;
      controls.innerHTML = '';

      if (totalPages > 1) {
        const prevBtn = document.createElement('button');
        prevBtn.textContent = '<';
        prevBtn.className = 'pagination-prev';

        if (page === 1) {
          prevBtn.disabled = true;
          prevBtn.classList.add('in-active');
        } else {
          prevBtn.onclick = () => {
            currentPage = page - 1;
            renderPage(currentPage, true);
          };
        }
        controls.appendChild(prevBtn);

        for (let i = 1; i <= totalPages; i++) {
          const btn = document.createElement('button');
          btn.textContent = i;

          if (i === page) {
            btn.classList.add('in-active');
          } else {
            btn.onclick = () => {
              currentPage = i;
              renderPage(currentPage, true);
            };
          }
          controls.appendChild(btn);
        }

        const nextBtn = document.createElement('button');
        nextBtn.textContent = '>';
        nextBtn.className = 'pagination-next';

        if (page === totalPages) {
          nextBtn.disabled = true;
          nextBtn.classList.add('in-active');
        } else {
          nextBtn.onclick = () => {
            currentPage = page + 1;
            renderPage(currentPage, true);
          };
        }
        controls.appendChild(nextBtn);

      } else {
        wrapper.style.display = 'none';
      }

      if (autoScroll) {
        const sectionBox = gallery.closest('.section-box');
        if (sectionBox) {
          const scrollContainer = window.utils.getExplicitScrollableAncestor(sectionBox);
          requestAnimationFrame(() => {
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

    window.addEventListener('resize', () => {
      pages = buildPages();

      if (currentPage > pages.length) {
        currentPage = pages.length;
      }

      renderPage(currentPage);
    });
  }

  window.paginateGallery = setupPagination;

  document.addEventListener('DOMContentLoaded', () => {
    document.querySelectorAll('.image-gallery--justified, .image-gallery--aspect')
      .forEach(gallery => {
        const hasSearch = !!document.getElementById('search-input');
        if (hasSearch && gallery.id === 'imageGallery') return;

        const wrappers = Array.from(gallery.querySelectorAll('.image-wrapper'));
        const pageSize = parseInt(gallery.dataset.pageSize) || IMAGES_PER_PAGE_DEFAULT;

        setupPagination(gallery, wrappers, pageSize);
      });
  });

})();
