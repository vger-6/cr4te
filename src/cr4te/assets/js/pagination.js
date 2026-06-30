(function () {
  const cr4te = window.cr4te = window.cr4te || {};
  cr4te.pagination = cr4te.pagination || {};
  cr4te.galleries = cr4te.galleries || {};
  cr4te.lightbox = cr4te.lightbox || {};

  const PAGE_ROWS_DEFAULT = 5;
  const instances = new WeakMap();
  const ROW_TOP_TOLERANCE = 4;

  function parsePositiveInt(value, fallback) {
    const parsed = parseInt(value, 10);
    return Number.isFinite(parsed) && parsed > 0 ? parsed : fallback;
  }

  function rebuildGallery(gallery) {
    if (gallery.classList.contains('image-gallery--justified')) {
      cr4te.galleries.rebuildJustified?.(gallery);
    } else if (gallery.classList.contains('image-gallery--aspect')) {
      cr4te.galleries.rebuildAspect?.(gallery);
    }
  }

  function rebindLightbox() {
    cr4te.lightbox.rebind?.();
  }

  function getLayoutMetrics(gallery) {
    const computedStyle = window.getComputedStyle(gallery);
    const gap = window.utils.parseCssLength(
      computedStyle.columnGap || computedStyle.gap || "1rem",
      gallery
    );
    const galleryWidth = gallery.clientWidth;
    const maxHeight = parseFloat(gallery.dataset.imageMaxHeight || "200");

    return {
      gap: Number.isFinite(gap) ? gap : 16,
      galleryWidth,
      maxHeight: Number.isFinite(maxHeight) && maxHeight > 0 ? maxHeight : 200,
    };
  }

  function getRatio(wrapper) {
    const w = parseFloat(wrapper.dataset.width);
    const h = parseFloat(wrapper.dataset.height);
    if (!w || !h) return 1;
    return w / h;
  }

  function chunkRows(items, rowSize) {
    const rows = [];
    const safeRowSize = Math.max(rowSize, 1);

    for (let index = 0; index < items.length; index += safeRowSize) {
      rows.push(items.slice(index, index + safeRowSize));
    }

    return rows;
  }

  function calculateAspectColumns(gallery, allWrappers) {
    const { w, h } = window.utils.parseAspectRatio(gallery.dataset.aspectRatio);
    const { gap, galleryWidth, maxHeight } = getLayoutMetrics(gallery);

    if (!galleryWidth || allWrappers.length === 0) return 1;

    let columns = 1;
    while (columns < allWrappers.length) {
      const totalGap = gap * (columns - 1);
      const availableWidth = Math.max(galleryWidth - totalGap, 1);
      const itemWidth = availableWidth / columns;
      const itemHeight = itemWidth * (h / w);

      if (itemHeight <= maxHeight) break;
      columns++;
    }

    return columns;
  }

  function buildAspectRows(gallery, allWrappers) {
    return chunkRows(allWrappers, calculateAspectColumns(gallery, allWrappers));
  }

  function buildJustifiedRows(gallery, allWrappers) {
    const { gap, galleryWidth, maxHeight } = getLayoutMetrics(gallery);

    if (!galleryWidth) return chunkRows(allWrappers, 1);

    const rows = [];
    let row = [];
    let ratioSum = 0;

    allWrappers.forEach(wrapper => {
      row.push(wrapper);
      ratioSum += getRatio(wrapper);

      const totalGap = gap * (row.length - 1);
      const rowHeight = (galleryWidth - totalGap) / ratioSum;

      if (rowHeight <= maxHeight) {
        rows.push(row);
        row = [];
        ratioSum = 0;
      }
    });

    if (row.length > 0) {
      rows.push(row);
    }

    return rows;
  }

  function buildMeasuredRows(gallery, allWrappers) {
    if (allWrappers.length === 0) return [];

    gallery.innerHTML = '';
    allWrappers.forEach(wrapper => gallery.appendChild(wrapper));

    const rows = [];
    let currentTop = null;

    allWrappers.forEach(wrapper => {
      const top = Math.round(wrapper.getBoundingClientRect().top);

      if (currentTop === null || Math.abs(top - currentTop) > ROW_TOP_TOLERANCE) {
        rows.push([]);
        currentTop = top;
      }

      rows[rows.length - 1].push(wrapper);
    });

    return rows;
  }

  function buildRowsForGallery(gallery, allWrappers) {
    if (gallery.classList.contains('image-gallery--justified')) {
      return buildJustifiedRows(gallery, allWrappers);
    }

    if (gallery.classList.contains('image-gallery--aspect')) {
      return buildAspectRows(gallery, allWrappers);
    }

    return buildMeasuredRows(gallery, allWrappers);
  }

  function chunkRowsIntoPages(rows, pageRows) {
    const pages = [];

    for (let index = 0; index < rows.length; index += pageRows) {
      pages.push(rows.slice(index, index + pageRows).flat());
    }

    return pages;
  }

  function createPagination(gallery, initialWrappers, initialPageRows) {
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

    let allWrappers = initialWrappers;
    let pageRows = parsePositiveInt(initialPageRows, PAGE_ROWS_DEFAULT);
    let currentPage = 1;

    function buildPages() {
      return chunkRowsIntoPages(buildRowsForGallery(gallery, allWrappers), pageRows);
    }

    let pages = buildPages();

    function renderPage(page, autoScroll = false) {
      const visibleWrappers = pages[page - 1] || [];

      gallery.innerHTML = '';
      visibleWrappers.forEach(wrapper => gallery.appendChild(wrapper));

      rebuildGallery(gallery);
      rebindLightbox();

      const totalPages = pages.length;
      controls.innerHTML = '';
      wrapper.style.display = totalPages > 1 ? '' : 'none';

      if (totalPages > 1) {
        const previousLabel = gallery.dataset.previousLabel || 'Previous';
        const nextLabel = gallery.dataset.nextLabel || 'Next';

        const prevBtn = document.createElement('button');
        prevBtn.textContent = '<';
        prevBtn.className = 'pagination-prev';
        prevBtn.setAttribute('aria-label', previousLabel);

        if (page === 1) {
          prevBtn.disabled = true;
          prevBtn.classList.add('in-active');
        } else {
          prevBtn.title = previousLabel;
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
            btn.disabled = true;
            btn.setAttribute('aria-current', 'page');
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
        nextBtn.setAttribute('aria-label', nextLabel);

        if (page === totalPages) {
          nextBtn.disabled = true;
          nextBtn.classList.add('in-active');
        } else {
          nextBtn.title = nextLabel;
          nextBtn.onclick = () => {
            currentPage = page + 1;
            renderPage(currentPage, true);
          };
        }
        controls.appendChild(nextBtn);
      }

      if (autoScroll) {
        const sectionBox = gallery.closest('.section-box');
        if (sectionBox) {
          const scrollContainer = window.utils.getExplicitScrollableAncestor(sectionBox);
          requestAnimationFrame(() => {
            if (scrollContainer) {
              scrollContainer.scrollTo({
                top: sectionBox.offsetTop - scrollContainer.offsetTop,
                behavior: window.utils.prefersReducedMotion() ? 'auto' : 'smooth'
              });
            }
          });
        }
      }
    }

    function handleResize() {
      pages = buildPages();

      if (currentPage > pages.length) {
        currentPage = Math.max(pages.length, 1);
      }

      renderPage(currentPage);
    }

    function update(nextWrappers, nextPageRows) {
      allWrappers = nextWrappers;
      pageRows = parsePositiveInt(nextPageRows, PAGE_ROWS_DEFAULT);
      currentPage = 1;
      pages = buildPages();
      renderPage(currentPage);
    }

    window.addEventListener('resize', handleResize);
    renderPage(currentPage);

    return {
      update,
      destroy() {
        window.removeEventListener('resize', handleResize);
      }
    };
  }

  function setupPagination(gallery, allWrappers, pageRows = PAGE_ROWS_DEFAULT) {
    if (!gallery) return;

    pageRows = parsePositiveInt(pageRows, PAGE_ROWS_DEFAULT);

    const instance = instances.get(gallery);
    if (instance) {
      instance.update(allWrappers, pageRows);
      return;
    }

    instances.set(gallery, createPagination(gallery, allWrappers, pageRows));
  }

  cr4te.pagination.mount = setupPagination;

  cr4te.onReady(() => {
    document.querySelectorAll('.image-gallery--justified, .image-gallery--aspect')
      .forEach(gallery => {
        const hasSearch = !!document.getElementById('search-input');
        if (hasSearch && gallery.id === 'imageGallery') return;

        const wrappers = Array.from(gallery.querySelectorAll('.image-wrapper'));
        const pageRows = parsePositiveInt(gallery.dataset.pageRows, PAGE_ROWS_DEFAULT);

        setupPagination(gallery, wrappers, pageRows);
      });
  });

})();
