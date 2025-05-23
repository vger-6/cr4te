//TODO: DRY up code duplication in filter_projects.js and filter_creators.js
//TODO: Debounce input events for large galleries

document.addEventListener("DOMContentLoaded", function () {
  const searchInput = document.getElementById("search-input");
  const tabs = document.querySelectorAll(".az-tab");
  const gallery = document.getElementById("imageGallery");

  // Cache all original wrappers once
  let allWrappers = Array.from(gallery.querySelectorAll(".image-wrapper"));

  // Replace gallery content initially
  gallery.innerHTML = '';
  allWrappers.forEach(w => gallery.appendChild(w));

  function filterProjects() {
    const query = searchInput.value.trim().toLowerCase();
    const selectedTab = document.querySelector(".az-tab.active");
    const letter = selectedTab ? selectedTab.dataset.letter.toLowerCase() : null;

    const terms = query.split(/\s+/).filter(Boolean);

    // Filter wrappers based on title/text/letter
    const visibleWrappers = allWrappers.filter(entry => {
      const title = entry.dataset.title.toLowerCase();
      const searchText = entry.dataset.text?.toLowerCase() || '';

      const matchesAllTerms = terms.every(term =>
        title.includes(term) || searchText.includes(term)
      );

      const matchesLetter = letter && title.startsWith(letter);

      return query ? matchesAllTerms : matchesLetter;
    });

    // Replace gallery content
    gallery.innerHTML = '';
    visibleWrappers.forEach(w => gallery.appendChild(w));

    // Recalculate layout
    // rebuildImageGallery.?();
    if (typeof rebuildImageGallery === 'function') {
      rebuildImageGallery();
    }
  }

  // Hook up search and tab filters
  searchInput.addEventListener("input", () => {
    tabs.forEach(t => t.classList.remove("active"));
    filterProjects();
  });
  
  tabs.forEach(tab => {
    tab.addEventListener("click", () => {
      tabs.forEach(t => t.classList.remove("active"));
      tab.classList.add("active");
      searchInput.value = "";
      filterProjects();
    });
  });
  
  // Activate 'A' tab by default
  const defaultTab = document.querySelector('.az-tab[data-letter="A"]');
  if (defaultTab) {
    defaultTab.classList.add("active");
    filterProjects();
  }

  // Initial layout
  filterProjects();
});

