const body = document.body;
const savedLanguage = localStorage.getItem("neuroflow-docs-language");
body.dataset.language = savedLanguage === "en" ? "en" : "zh";

const languageButton = document.querySelector("[data-language-toggle]");
if (languageButton) {
  const updateLabel = () => {
    languageButton.textContent = body.dataset.language === "zh" ? "EN" : "中文";
  };
  languageButton.addEventListener("click", () => {
    body.dataset.language = body.dataset.language === "zh" ? "en" : "zh";
    localStorage.setItem("neuroflow-docs-language", body.dataset.language);
    updateLabel();
  });
  updateLabel();
}

const menuButton = document.querySelector("[data-menu-toggle]");
if (menuButton) {
  menuButton.addEventListener("click", () => {
    body.classList.toggle("sidebar-open");
  });
}

const searchInput = document.querySelector("[data-doc-search]");
if (searchInput) {
  searchInput.addEventListener("input", () => {
    const query = searchInput.value.trim().toLowerCase();
    document.querySelectorAll("[data-searchable]").forEach((element) => {
      const matches = !query || element.textContent.toLowerCase().includes(query);
      element.classList.toggle("search-hidden", !matches);
    });
  });
}

