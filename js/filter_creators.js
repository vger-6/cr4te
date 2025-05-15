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
  const entries = document.querySelectorAll(".creator-entry");

  input.addEventListener("input", () => {
    const terms = input.value.toLowerCase().match(/"[^"]+"|\S+/g) || [];

    entries.forEach(entry => {
      const haystack = entry.dataset.search || "";
      const matches = terms.every(term =>
        haystack.includes(term.replace(/"/g, ""))
      );
      entry.style.display = matches ? "" : "none";
    });
  });

  console.log("Filter initialized");
});
