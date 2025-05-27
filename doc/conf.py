"""Sphinx configuration file for an LSST stack package.
This configuration only affects single-package Sphinx documentation builds.
"""

import asyncio
import logging
import os
import sys

# Add current directory to Python path so we can import local extensions
sys.path.insert(0, os.path.abspath("."))

logging.basicConfig(level=logging.INFO)

# Monkey patch asyncio.run to prevent script execution during
# documentation building
original_asyncio_run = asyncio.run


def mock_asyncio_run(coro):
    """Mock implementation of asyncio.run that prevents execution."""
    logging.debug(
        f"Skipping execution of coroutine during documentation" f" building: {coro}"
    )
    return None


asyncio.run = mock_asyncio_run

os.environ["LSST_TOPIC_SUBNAME"] = "test"

original_exit = sys.exit


def mock_exit(code=None):
    """Mock implementation of sys.exit that prevents exiting."""
    logging.debug(f"Skipping sys.exit({code}) during documentation building")
    return None


sys.exit = mock_exit


class MockNamespace:
    """Mock namespace for script arguments."""

    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)


import lsst.ts.standardscripts  # noqa
from documenteer.conf.pipelinespkg import *  # type: ignore # noqa

project = "ts_standardscripts"
html_theme_options["logotext"] = project  # type: ignore # noqa
html_title = project
html_short_title = project
doxylink = {}  # Avoid warning: Could not find tag file _doxygen/doxygen.tag

extensions.append("sphinx_script_categorizer")  # type: ignore # noqa

html_static_path = ["_static"]  # type: ignore # noqa
html_css_files = ["custom.css"]  # type: ignore # noqa

intersphinx_mapping["ts_observatory_control"] = (  # type: ignore # noqa
    "https://ts-observatory-control.lsst.io",
    None,
)
intersphinx_mapping["ts_salobj"] = ("https://ts-salobj.lsst.io", None)  # type: ignore # noqa
intersphinx_mapping["ts_utils"] = ("https://ts-utils.lsst.io", None)  # type: ignore # noqa
intersphinx_mapping["ts_xml"] = ("https://ts-xml.lsst.io", None)  # type: ignore # noqa
