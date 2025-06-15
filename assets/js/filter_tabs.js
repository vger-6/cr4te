document.addEventListener("DOMContentLoaded", () => {
  const input = document.getElementById("search-input");
  const tabs = document.querySelectorAll(".az-tab");
  const { gallery, allWrappers } = FilterBase.getAllWrappers("#imageGallery");

  function filter() {
    const query = input.value.trim().toLowerCase();
    const selectedTab = document.querySelector(".az-tab.active");
    const letter = selectedTab ? selectedTab.dataset.letter.toLowerCase() : null;
    const terms = FilterBase.extractTerms(query);

    const visible = allWrappers.filter(entry => {
      const azString = entry.dataset.azString.toLowerCase();
      const searchText = entry.dataset.searchText?.toLowerCase() || '';
      const matchesTerms = terms.every(term =>
        searchText.includes(term)
      );
      const matchesLetter = letter && azString.startsWith(letter);
      return query ? matchesTerms : matchesLetter;
    });

    FilterBase.filterAndPaginate(gallery, visible);
  }

  input.addEventListener("input", () => {
    tabs.forEach(t => t.classList.remove("active"));
    filter();
  });

  tabs.forEach(tab => {
    tab.addEventListener("click", () => {
      tabs.forEach(t => t.classList.remove("active"));
      tab.classList.add("active");
      input.value = "";
      filter();
    });
  });

  const defaultTab = document.querySelector('.az-tab[data-letter="A"]');
  if (defaultTab) {
    defaultTab.classList.add("active");
  }

  filter();
});

