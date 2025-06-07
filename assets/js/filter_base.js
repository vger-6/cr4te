window.FilterBase = {
  getAllWrappers(gallerySelector) {
    const gallery = document.querySelector(gallerySelector);
    return {
      gallery,
      allWrappers: Array.from(gallery.querySelectorAll(".image-wrapper"))
    };
  },
  filterAndRender(gallery, wrappers) {
    if (!gallery) return;
    
    gallery.innerHTML = '';
    wrappers.forEach(w => gallery.appendChild(w));
    if (typeof rebuildImageGallery === 'function') {
      rebuildImageGallery();
    }
  }
};

