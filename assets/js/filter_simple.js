document.addEventListener("DOMContentLoaded", () => {
  const input = document.getElementById("search-input");
  const { gallery, allWrappers } = FilterBase.getAllWrappers("#imageGallery");

  function filter() {
    const terms = FilterBase.extractTerms(input.value);
    const visible = allWrappers.filter(entry => {
      const searchText = entry.dataset.searchText?.toLowerCase() || "";
      return terms.every(term => searchText.includes(term));
    });

    FilterBase.filterAndPaginate(gallery, visible);
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

