# Configuration file for the Sphinx documentation builder.
#
# This file only contains a selection of the most common options. For a full
# list see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

import importlib
import logging
import os
import sys
import typing
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from typing import Any, Dict, List
    from sphinx.application import Sphinx

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
#logging.basicConfig(level=logging.DEBUG)

# -- Path setup --------------------------------------------------------------

# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.
#
# import os
# import sys
# sys.path.insert(0, os.path.abspath('.'))


# -- Project information -----------------------------------------------------

project = 'darc'
copyright = '2019-2021, Jarry Shaw'  # pylint: disable=redefined-builtin
author = 'Jarry Shaw'

# The full version, including alpha/beta/rc tags
release = '1.0.0'


# -- General configuration ---------------------------------------------------

# Add any Sphinx extension module names here, as strings. They can be
# extensions coming with Sphinx (named 'sphinx.ext.*') or your custom
# ones.
extensions = [
    'sphinx.ext.viewcode',
    'sphinx.ext.intersphinx',
    'sphinx.ext.autodoc', 'sphinx.ext.autodoc.typehints',
    'sphinx.ext.napoleon',
    'sphinx.ext.todo',
    'sphinx_autodoc_typehints',
]

intersphinx_mapping = {
    'python': ('https://docs.python.org/3', None),

    'requests': ('https://requests.readthedocs.io/en/latest/', None),
    'selenium': ('https://www.selenium.dev/selenium/docs/api/py/', None),
    'stem': ('https://stem.torproject.org/', None),
}

autodoc_default_options = {
    'members': True,
    'member-order': 'groupwise',
    'special-members': '__init__',
    'undoc-members': True,
    'exclude-members': '__weakref__, _abc_impl, _unbound_fields, _wtforms_meta, _meta, _schema',
    'ignore-module-all': True,
    'private-members': True,
}
autodoc_typehints = 'description'
# autodoc_member_order = 'bysource'
# autodoc_member_order = 'alphabetic'

# Napoleon settings
napoleon_google_docstring = True
napoleon_numpy_docstring = True
napoleon_include_init_with_doc = True
napoleon_include_private_with_doc = True
napoleon_include_special_with_doc = True
napoleon_use_admonition_for_examples = True
napoleon_use_admonition_for_notes = True
napoleon_use_admonition_for_references = True
napoleon_use_ivar = True
napoleon_use_param = True
napoleon_use_rtype = True
napoleon_use_keyword = True
napoleon_custom_sections = None

manpages_url = 'https://linux.die.net/man/{section}/{page}'

do_include_todos = True

set_type_checking_flag = True
typehints_fully_qualified = False
always_document_param_types = False
typehints_document_rtype = True

# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
# This pattern also affects html_static_path and html_extra_path.
exclude_patterns = []  # type: List[str]


# -- Options for HTML output -------------------------------------------------

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
#
html_theme = 'alabaster'

# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
html_static_path = ['_static']

# Theme options are theme-specific and customize the look and feel of a theme
# further.  For a list of options available for each theme, see the
# documentation.
html_theme_options = {
    'show_powered_by': False,
    'github_user': 'JarryShaw',
    'github_repo': 'darc',
    'github_banner': True,
    'github_type': 'star',
    #'show_related': False,
    #'note_bg': '#FFF59C',
    #'travis_button': True,
    #'codecov_button': True,
}


# -- Customised hooks --------------------------------------------------------

os.environ['TOR_PASS'] = 'null'


def maybe_skip_member(app: 'Sphinx', what: str, name: str,  # pylint: disable=unused-argument
                      obj: 'Any', skip: bool, options: 'Dict[str, Any]') -> bool:  # pylint: disable=unused-argument
    if name == '_abc_impl':
        return True
    if name == '__init__':
        if '__create_fn__' in obj.__qualname__:
            return True
    return skip


def remove_module_docstring(app: 'Sphinx', what: str, name: str,  # pylint: disable=unused-argument
                            obj: 'Any', options: 'Dict[str, Any]', lines: 'List[str]') -> None:  # pylint: disable=unused-argument
    if what == "module" and "darc" in name:
        module = sys.modules.get(name)
        if module is not None:
            logger.info('reloading module: %s', name)
            typing.TYPE_CHECKING = True
            importlib.reload(module)
            logger.info('reloaded module: %s', name)
        #lines.clear()


def process_docstring(app: 'Sphinx', what: str, name: str,  # pylint: disable=unused-argument
                      obj: 'Any', options: 'Dict[str, Any]', lines: 'List[str]') -> None:  # pylint: disable=unused-argument
    if what == "module" and "darc" in name:
        module = importlib.import_module(name)
        typing.TYPE_CHECKING = True
        importlib.reload(module)


def source_read(app: 'Sphinx', docname: str, source_text: str) -> None:  # pylint: disable=unused-argument
    print(docname, source_text)


def setup(app: 'Sphinx') -> None:
    #app.connect('autodoc-process-docstring', process_docstring, 0)
    #app.connect("autodoc-process-docstring", remove_module_docstring)
    app.connect('autodoc-skip-member', maybe_skip_member)
    #app.connect('source-read', source_read)

    # typing.TYPE_CHECKING = True
    # for name, module in sys.modules.copy().items():
    #     if 'darc' not in name:
    #         continue

    #     logger.info('reloading module: %s', name)
    #     importlib.reload(module)
    #     logger.info('reloaded module: %s', name)
