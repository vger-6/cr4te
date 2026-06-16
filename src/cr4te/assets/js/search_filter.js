(function () {
  const cr4te = window.cr4te = window.cr4te || {};
  cr4te.pagination = cr4te.pagination || {};
  cr4te.galleries = cr4te.galleries || {};
  cr4te.lightbox = cr4te.lightbox || {};

  function getAllWrappers(gallerySelector) {
    const gallery = document.querySelector(gallerySelector);
    return {
      gallery,
      allWrappers: gallery ? Array.from(gallery.querySelectorAll(".image-wrapper")) : []
    };
  }

  function extractTerms(query) {
    return query
      .match(/"[^"]+"|\S+/g)
      ?.map(term => term.replace(/"/g, "").toLowerCase()) || [];
  }

  function filterAndPaginate(gallery, wrappers) {
    if (!gallery) return;

    const pageSize = parseInt(gallery.dataset.pageSize || "0", 10);
    const noPagination = gallery.dataset.noPagination === "true";

    if (!noPagination && pageSize > 0 && typeof cr4te.pagination.mount === "function") {
      cr4te.pagination.mount(gallery, wrappers, pageSize);
    } else {
      gallery.innerHTML = '';
      wrappers.forEach(wrapper => gallery.appendChild(wrapper));
      cr4te.galleries.rebuildJustified?.();
      cr4te.galleries.rebuildAspect?.();
      cr4te.lightbox.rebind?.();
    }
  }

  cr4te.onReady(() => {
    const input = document.getElementById("search-input");
    const clearBtn = document.getElementById("clear-search");
    const noResults = document.querySelector(".empty-state--search");
    const { gallery, allWrappers } = getAllWrappers("#imageGallery");

    if (!input || !clearBtn || !gallery) return;

    function setNoResultsState(show) {
      if (noResults) {
        const shouldBeHidden = !show;
        if (noResults.hidden !== shouldBeHidden) {
          noResults.hidden = shouldBeHidden;
        }
      }
      gallery.hidden = show;
    }

    function filter() {
      const terms = extractTerms(input.value);
      const visible = allWrappers.filter(entry => {
        const searchText = entry.dataset.searchText?.toLowerCase() || "";
        return terms.every(term => searchText.includes(term));
      });
      const hasQuery = terms.length > 0;
      const showNoResults = hasQuery && visible.length === 0;

      clearBtn.style.display = input.value ? "block" : "none";
      gallery.hidden = false;
      filterAndPaginate(gallery, visible);
      setNoResultsState(showNoResults);
    }

    const params = new URLSearchParams(window.location.search);
    const tag = params.get('tag');
    if (tag && input) {
      input.value = tag;
      window.utils.clearUrlParam('tag');
    }

    input.addEventListener("input", filter);

    clearBtn.addEventListener("click", () => {
      input.value = "";
      input.focus();
      filter();
    });
    
    input.addEventListener("keydown", (event) => {
      if (event.key === "Escape") {
        input.value = "";
        input.dispatchEvent(new Event("input")); // re-trigger filtering
      }
    });
    
    window.addEventListener("pageshow", () => {
      input.dispatchEvent(new Event("input")); // re-trigger filtering
    });

    // Initial run
    filter();
  });
})();

