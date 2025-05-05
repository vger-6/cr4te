document.addEventListener("DOMContentLoaded", function () {
  const searchInput = document.getElementById("search-input");
  const tabs = document.querySelectorAll(".az-tab");
  const projects = document.querySelectorAll(".project-entry");

  function filterProjects() {
    const query = searchInput.value.trim().toLowerCase();
    const selectedTab = document.querySelector(".az-tab.active");
    const letter = selectedTab ? selectedTab.dataset.letter.toLowerCase() : null;

    const terms = query.split(/\s+/).filter(Boolean);

    projects.forEach(entry => {
      const title = entry.dataset.title.toLowerCase();
      const searchText = entry.dataset.text.toLowerCase();

      const matchesAllTerms = terms.every(term =>
        title.includes(term) || searchText.includes(term)
      );

      const matchesLetter = letter && title.startsWith(letter);

      entry.style.display = (query ? matchesAllTerms : matchesLetter) ? "" : "none";
    });
  }

  tabs.forEach(tab => {
    tab.addEventListener("click", function () {
      tabs.forEach(t => t.classList.remove("active"));
      this.classList.add("active");
      searchInput.value = "";
      filterProjects();
    });
  });

  searchInput.addEventListener("input", () => {
    tabs.forEach(t => t.classList.remove("active"));
    filterProjects();
  });

  // Activate 'A' tab by default
  const defaultTab = document.querySelector('.az-tab[data-letter="A"]');
  if (defaultTab) {
    defaultTab.classList.add("active");
    filterProjects();
  }
});
