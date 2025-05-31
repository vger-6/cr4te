//TODO: DRY up code duplication in filter_projects.js and filter_creators.js
//TODO: Debounce input events for large galleries

window.addEventListener('DOMContentLoaded', () => {
  const params = new URLSearchParams(window.location.search);
  const tag = params.get('tag');
  if (tag) {
    const searchInput = document.getElementById('search-input');
    if (searchInput) {
      searchInput.value = tag;
      const event = new Event('input', { bubbles: true });
      searchInput.dispatchEvent(event); // Trigger filter
    }
  }
});

document.addEventListener("DOMContentLoaded", () => {
  const input = document.getElementById("search-input");
  const gallery = document.getElementById("imageGallery");

  // Cache all original entries
  let allWrappers = Array.from(gallery.querySelectorAll(".image-wrapper"));

  // Clear and re-insert once to reset layout
  gallery.innerHTML = '';
  allWrappers.forEach(w => gallery.appendChild(w));

  function filterCreators() {
    const terms = input.value.toLowerCase().match(/"[^"]+"|\S+/g) || [];

    const visibleWrappers = allWrappers.filter(entry => {
      const haystack = entry.dataset.search || "";
      return terms.every(term =>
        haystack.includes(term.replace(/"/g, ""))
      );
    });

    // Update DOM with filtered results
    gallery.innerHTML = '';
    visibleWrappers.forEach(w => gallery.appendChild(w));

    // Recalculate layout
    if (typeof rebuildImageGallery === 'function') {
      rebuildImageGallery();
    }
  }

  input.addEventListener("input", filterCreators);

  // Initial layout render
  filterCreators();
});

