from pallets_sphinx_themes import get_version
from pallets_sphinx_themes import ProjectLink

# Project --------------------------------------------------------------

project = "CacheLib"
copyright = "2018 Pallets"
author = "Pallets"
release, version = get_version("cachelib")

# General --------------------------------------------------------------

default_role = "code"
extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.extlinks",
    "sphinx.ext.intersphinx",
    "sphinxcontrib.log_cabinet",
    "sphinx_tabs.tabs",
    "pallets_sphinx_themes",
]
autodoc_member_order = "bysource"
autodoc_typehints = "description"
autodoc_preserve_defaults = True
extlinks = {
    "issue": ("https://github.com/pallets-eco/cachelib/issues/%s", "#%s"),
    "pr": ("https://github.com/pallets-eco/cachelib/pull/%s", "#%s"),
    "ghsa": (
        "https://github.com/pallets-eco/cachelib/security/advisories/GHSA-%s",
        "GHSA-%s",
    ),
}
intersphinx_mapping = {
    "python": ("https://docs.python.org/3/", None),
}

# HTML -----------------------------------------------------------------

html_theme = "werkzeug"
html_theme_options = {"index_sidebar_logo": False}
html_context = {
    "project_links": [
        ProjectLink("Donate", "https://palletsprojects.com/donate"),
        ProjectLink("PyPI Releases", "https://pypi.org/project/cachelib/"),
        ProjectLink("Source Code", "https://github.com/pallets-eco/cachelib/"),
        ProjectLink("Issue Tracker", "https://github.com/pallets-eco/cachelib/issues/"),
        ProjectLink("Chat", "https://discord.gg/pallets"),
    ]
}
html_sidebars = {
    "index": ["project.html", "localtoc.html", "searchbox.html", "ethicalads.html"],
    "**": ["localtoc.html", "relations.html", "searchbox.html", "ethicalads.html"],
}
singlehtml_sidebars = {"index": ["project.html", "localtoc.html", "ethicalads.html"]}
html_title = f"{project} Documentation ({version})"
html_show_sourcelink = False
