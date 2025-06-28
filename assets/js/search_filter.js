(function () {
  function getAllWrappers(gallerySelector) {
    const gallery = document.querySelector(gallerySelector);
    return {
      gallery,
      allWrappers: Array.from(gallery.querySelectorAll(".image-wrapper"))
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

    if (!noPagination && pageSize > 0 && typeof window.paginateGallery === "function") {
      window.paginateGallery(gallery, wrappers, pageSize);
    } else {
      gallery.innerHTML = '';
      wrappers.forEach(wrapper => gallery.appendChild(wrapper));
      if (typeof rebuildJustifiedImageGallery === 'function') rebuildJustifiedImageGallery();
      if (typeof rebuildAspectImageGallery === 'function') rebuildAspectImageGallery();
      if (typeof rebindLightbox === 'function') rebindLightbox();
    }
  }

  document.addEventListener("DOMContentLoaded", () => {
    const input = document.getElementById("search-input");
    const { gallery, allWrappers } = getAllWrappers("#imageGallery");

    function filter() {
      const terms = extractTerms(input.value);
      const visible = allWrappers.filter(entry => {
        const searchText = entry.dataset.searchText?.toLowerCase() || "";
        return terms.every(term => searchText.includes(term));
      });

      filterAndPaginate(gallery, visible);
    }

    // Set search from query param
    const params = new URLSearchParams(window.location.search);
    const tag = params.get('tag');
    if (tag && input) {
      input.value = tag;
    }

    input.addEventListener("input", filter);

    // Initial run
    filter();
  });
})();

