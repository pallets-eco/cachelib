import sys

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
    "sphinx_copybutton",
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

# -- Options for copy button ---------------------------------------------------

# virtual env prefix: (venv), (cachelib-venv), (testenv)
venv = r"\((?:(?:cachelib-)?venv|testvenv)\)"
# macOS and Linux shell prompt: $
shell = r"\$"
# win CMD prompt: C:\>, C:\...>
cmd = r"C:\\>|C:\\\.\.\.>"
# PowerShell prompt: PS C:\>, PS C:\...>
ps = r"PS C:\\>|PS C:\\\.\.\.>"
# zero or one whitespace char
sp = r"\s?"

# optional venv prefix
venv_prefix = rf"(?:{venv})?"
# one of the platforms' shell prompts
shell_prompt = rf"(?:{shell}|{cmd}|{ps})"

copybutton_prompt_text = "|".join(
    [
        # Python REPL
        # r">>>\s?", r"\.\.\.\s?",
        # IPython and Jupyter
        # r"In \[\d*\]:\s?", r" {5,8}:\s?", r" {2,5}\.\.\.:\s?",
        # Shell prompt
        rf"{venv_prefix}{sp}{shell_prompt}{sp}",
    ]
)
copybutton_prompt_is_regexp = True
copybutton_remove_prompts = True
copybutton_only_copy_prompt_lines = True
copybutton_copy_empty_lines = False

# -- Options for spelling -------------------------------------------

# Spelling check needs an additional module that is not installed by default.
# Add it only if spelling check is requested so docs can be generated without it.
if "spelling" in sys.argv:
    extensions.append("sphinxcontrib.spelling")

# Spelling language.
spelling_lang = "en_US"

# Location of word list.
spelling_word_list_filename = "spelling_wordlist"
