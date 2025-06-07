document.addEventListener("DOMContentLoaded", () => {
  const input = document.getElementById("search-input");
  const { gallery, allWrappers } = FilterBase.getAllWrappers("#imageGallery");

  function filter() {
    const terms = input.value.toLowerCase().match(/"[^"]+"|\S+/g)?.map(term => term.replace(/"/g, "")) || [];
    const visible = allWrappers.filter(entry => {
      const searchText = entry.dataset.searchText?.toLowerCase() || "";
      return terms.every(term =>
        searchText.includes(term)
      );
    });
    FilterBase.filterAndRender(gallery, visible);
  }

  // Check for ?tag= query parameter and set the input value
  const params = new URLSearchParams(window.location.search);
  const tag = params.get('tag');
  if (tag && input) {
    input.value = tag;
  }

  input.addEventListener("input", filter);

  // Trigger initial filtering
  filter();
});

