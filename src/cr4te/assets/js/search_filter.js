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

  function parsePositivePage(value) {
    const parsed = parseInt(value, 10);
    return Number.isFinite(parsed) && parsed > 0 ? parsed : 1;
  }

  function overviewUrlState() {
    const params = new URLSearchParams(window.location.search);
    return {
      query: params.get("q") || params.get("tag") || "",
      page: parsePositivePage(params.get("page"))
    };
  }

  function cloneHistoryState() {
    const state = window.history.state;
    return state && typeof state === "object" && !Array.isArray(state) ? { ...state } : {};
  }

  function writeOverviewUrl(query, page, mode = "replace") {
    const params = new URLSearchParams(window.location.search);
    const normalizedPage = parsePositivePage(page);

    params.delete("tag");

    if (query.trim()) {
      params.set("q", query);
    } else {
      params.delete("q");
    }

    if (normalizedPage > 1) {
      params.set("page", String(normalizedPage));
    } else {
      params.delete("page");
    }

    const nextUrl = `${window.location.pathname}${params.toString() ? `?${params.toString()}` : ""}${window.location.hash}`;
    const currentUrl = `${window.location.pathname}${window.location.search}${window.location.hash}`;
    if (nextUrl === currentUrl) return;

    try {
      const method = mode === "push" ? "pushState" : "replaceState";
      window.history[method](cloneHistoryState(), "", nextUrl);
    } catch (error) {
      // Filtering and pagination should continue even when browser history mutation is restricted.
    }
  }

  function filterAndPaginate(gallery, wrappers, page, onPageChange) {
    if (!gallery) return;

    const pageRows = parseInt(gallery.dataset.pageRows || "0", 10);
    const noPagination = gallery.dataset.noPagination === "true";

    if (!noPagination && pageRows > 0 && typeof cr4te.pagination.mount === "function") {
      return cr4te.pagination.mount(gallery, wrappers, pageRows, {
        stateMode: "url",
        initialPage: page,
        onPageChange,
      });
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

    const initialState = overviewUrlState();
    input.value = initialState.query;

    function setNoResultsState(show) {
      if (noResults) {
        const shouldBeHidden = !show;
        if (noResults.hidden !== shouldBeHidden) {
          noResults.hidden = shouldBeHidden;
        }
      }
      gallery.hidden = show;
    }

    function filter({ page = 1, updateUrl = false, urlMode = "replace" } = {}) {
      const terms = extractTerms(input.value);
      const visible = allWrappers.filter(entry => {
        const searchText = entry.dataset.searchText?.toLowerCase() || "";
        return terms.every(term => searchText.includes(term));
      });
      const hasQuery = terms.length > 0;
      const showNoResults = hasQuery && visible.length === 0;

      clearBtn.style.display = input.value ? "block" : "none";
      gallery.hidden = false;
      const pagination = filterAndPaginate(gallery, visible, page, nextPage => {
        writeOverviewUrl(input.value, nextPage, "push");
      });
      setNoResultsState(showNoResults);

      if (updateUrl) {
        writeOverviewUrl(input.value, pagination?.getCurrentPage?.() || 1, urlMode);
      }
    }

    input.addEventListener("input", () => filter({ page: 1, updateUrl: true }));

    clearBtn.addEventListener("click", () => {
      input.value = "";
      input.focus();
      filter({ page: 1, updateUrl: true });
    });
    
    input.addEventListener("keydown", (event) => {
      if (event.key === "Escape") {
        input.value = "";
        input.dispatchEvent(new Event("input")); // re-trigger filtering
      }
    });

    window.addEventListener("popstate", () => {
      const state = overviewUrlState();
      input.value = state.query;
      filter({ page: state.page });
    });
    
    window.addEventListener("pageshow", () => {
      const state = overviewUrlState();
      input.value = state.query;
      filter({ page: state.page });
    });

    // Initial run
    filter({ page: initialState.page, updateUrl: true });
  });
})();

