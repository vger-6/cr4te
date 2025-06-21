window.FilterBase = {
  getAllWrappers(gallerySelector) {
    const gallery = document.querySelector(gallerySelector);
    return {
      gallery,
      allWrappers: Array.from(gallery.querySelectorAll(".image-wrapper"))
    };
  },

  extractTerms(query) {
    return query
      .match(/"[^"]+"|\S+/g)
      ?.map(term => term.replace(/"/g, "").toLowerCase()) || [];
  },

  filterAndPaginate(gallery, wrappers) {
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
};

