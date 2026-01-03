# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

from __future__ import annotations

import sys
from pathlib import Path

# Add custom extensions directory to path
sys.path.insert(0, str(Path(__file__).parent / "extensions"))

project = "yamu"
AUTHOR = "Yamu contributors"
copyright = "2024, Yamu contributors"

master_doc = "index"
language = "en"
version = "0.1"
release = "0.1.0"

# -- General configuration ---------------------------------------------------

extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.autosummary",
    "sphinx.ext.extlinks",
    "sphinx.ext.viewcode",
    "sphinx_design",
    "sphinx_copybutton",
    "conf",
]

autosummary_generate = True
exclude_patterns = ["_build"]
templates_path = ["_templates"]
source_suffix = {".rst": "restructuredtext", ".md": "markdown"}

pygments_style = "sphinx"

# External links to the bug tracker and other sites.
extlinks = {
    "bug": ("https://github.com/yamu/yamu/issues/%s", "#%s"),
    "user": ("https://github.com/%s", "%s"),
    "pypi": ("https://pypi.org/project/%s/", "%s"),
    "stdlib": ("https://docs.python.org/3/library/%s.html", "%s"),
}

linkcheck_ignore = [
    r"https://github.com/yamu/yamu/issues/",
    r"https://github.com/[^/]+$",  # ignore user pages
    r".*localhost.*",
    r"https?://127\.0\.0\.1",
]

# Options for HTML output
htmlhelp_basename = "yamudoc"

# Options for LaTeX output
latex_documents = [("index", "yamu.tex", "yamu Documentation", AUTHOR, "manual")]

# Options for manual page output
man_pages = [
    (
        "reference/cli",
        "yamu",
        "game library manager",
        [AUTHOR],
        1,
    ),
    (
        "reference/config",
        "yamuconfig",
        "yamu configuration file",
        [AUTHOR],
        5,
    ),
]

# Global substitutions that can be used anywhere in the documentation.
rst_epilog = """
.. |Game| replace:: :class:`~yamu.library.models.Game`
.. |Library| replace:: :class:`~yamu.library.library.Library`
.. |Model| replace:: :class:`~yamu.dbcore.db.Model`
"""

# -- Options for HTML output -------------------------------------------------

html_theme = "pydata_sphinx_theme"
html_theme_options = {
    "collapse_navigation": False,
    "logo": {"text": "yamu"},
    "show_nav_level": 2,
    "navigation_depth": 4,
}
html_title = "yamu"
html_logo = "_static/yamu.png"
html_static_path = ["_static"]
html_css_files = ["yamu.css"]


def skip_member(app, what, name, obj, skip, options):
    if name.startswith("_"):
        return True
    return skip


def setup(app):
    app.connect("autodoc-skip-member", skip_member)
