from pallets_sphinx_themes import get_version
from pallets_sphinx_themes import ProjectLink

# Project -------------------------------------------------------------

project = "CacheLib"
copyright = "2020, Pallets Team"
author = "Pallets Team"
release, version = get_version("CacheLib")

# General -------------------------------------------------------------

# Add any Sphinx extension module names here, as strings. They can be
# extensions coming with Sphinx (named 'sphinx.ext.*') or your custom
# ones.

master_doc = "index"
extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.intersphinx",
    "pallets_sphinx_themes",
    "sphinxcontrib.log_cabinet",
    "sphinx_issues",
]
intersphinx_mapping = {"python": ("https://docs.python.org/3/", None)}
issues_github_path = "pallets/cachelib"

# HTML ----------------------------------------------------------------

html_theme = "jinja"
html_theme_options = {"index_sidebar_logo": False}
html_context = {
    "project_links": [
        ProjectLink("Donate to Pallets", "https://palletsprojects.com/donate"),
        ProjectLink("PyPI releases", "https://pypi.org/project/cachelib/"),
        ProjectLink("Source Code", "https://github.com/pallets/cachelib/"),
        ProjectLink("Issue Tracker", "https://github.com/pallets/cachelib/issues/"),
    ]
}
html_sidebars = {
    "index": ["project.html", "localtoc.html", "searchbox.html"],
    "**": ["localtoc.html", "relations.html", "searchbox.html"],
}
singlehtml_sidebars = {"index": ["project.html", "localtoc.html"]}
html_title = f"CacheLib Documentation ({version})"
html_show_sourcelink = False

# LaTeX ----------------------------------------------------------------

latex_documents = [
    (master_doc, f"Cachelib-{version}.tex", html_title, author, "manual")
]
