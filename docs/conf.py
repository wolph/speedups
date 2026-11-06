"""Sphinx configuration for the speedups guides.

The guides are Markdown files rendered through MyST. The configuration reads
the version from pyproject.toml so Read the Docs never has to compile the
Cython extensions to build the pages.
"""

from __future__ import annotations

import pathlib

import tomllib

DOCS_ROOT: pathlib.Path = pathlib.Path(__file__).resolve().parent
PROJECT_ROOT: pathlib.Path = DOCS_ROOT.parent

with (PROJECT_ROOT / 'pyproject.toml').open('rb') as fh:
    _metadata: dict[str, object] = tomllib.load(fh)['project']

project: str = 'speedups'
author: str = 'Rick van Hattem, Joren Hammudoglu'
copyright: str = 'Rick van Hattem'
release: str = str(_metadata['version'])
version: str = '.'.join(release.split('.')[:2])

extensions: list[str] = [
    'myst_parser',
    'sphinx.ext.intersphinx',
]

source_suffix: dict[str, str] = {'.md': 'markdown'}
master_doc: str = 'index'
smartquotes: bool = False
exclude_patterns: list[str] = ['_build', 'html', 'doctrees']

myst_enable_extensions: list[str] = ['colon_fence', 'deflist']
myst_heading_anchors: int = 3

intersphinx_mapping: dict[str, tuple[str, None]] = {
    'python': ('https://docs.python.org/3', None),
    'numpy': ('https://numpy.org/doc/stable', None),
    'psycopg': ('https://www.psycopg.org/psycopg3/docs', None),
}

html_theme: str = 'furo'
html_title: str = f'{project} {release}'
html_show_sphinx: bool = False
html_theme_options: dict[str, object] = {
    'source_repository': 'https://github.com/wolph/speedups/',
    'source_branch': 'develop',
    'source_directory': 'docs/',
}
