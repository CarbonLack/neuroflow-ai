from pathlib import Path

project = "NeuroEphys AI"
author = "NeuroEphys AI 团队"
copyright = "2026, NeuroEphys AI 团队"
release = "1.1.0"

extensions = [
    "sphinx.ext.autosectionlabel",
    "sphinx.ext.extlinks",
    "sphinx.ext.intersphinx",
    "sphinx_sitemap",
]
autosectionlabel_prefix_document = True
exclude_patterns = ["_build", "Thumbs.db", ".DS_Store"]
language = "zh_CN"

html_theme = "sphinx_rtd_theme"
html_title = "NeuroEphys AI 中文手册"
html_baseurl = "https://carbonlack.github.io/neuroflow-ai/zh/"
html_logo = str(
    Path(__file__).resolve().parents[3]
    / "assets"
    / "brand"
    / "neuroephys-ai-mark.svg"
)
html_favicon = html_logo
html_static_path = ["../_static"]
html_css_files = ["custom.css"]
html_theme_options = {
    "collapse_navigation": False,
    "navigation_depth": 4,
    "sticky_navigation": True,
    "includehidden": True,
}
html_extra_path = ["robots.txt"]
sitemap_url_scheme = "{link}"

intersphinx_mapping = {
    "spikeinterface": ("https://spikeinterface.readthedocs.io/en/stable/", None),
    "elephant": ("https://elephant.readthedocs.io/en/latest/", None),
}
