document.querySelectorAll("[data-language-link]").forEach((link) => {
  link.addEventListener("click", () => {
    localStorage.setItem("neuroflow-docs-language", link.dataset.languageLink);
  });
});

const menuButton = document.querySelector("[data-menu-toggle]");
if (menuButton) {
  menuButton.addEventListener("click", () => {
    document.body.classList.toggle("sidebar-open");
  });
}

const searchInput = document.querySelector("[data-doc-search]");
if (searchInput) {
  searchInput.addEventListener("input", () => {
    const query = searchInput.value.trim().toLocaleLowerCase();
    document.querySelectorAll("[data-searchable]").forEach((element) => {
      const text = element.textContent.toLocaleLowerCase();
      element.classList.toggle("search-hidden", Boolean(query) && !text.includes(query));
    });
  });
}
