#!/usr/bin/env python
# This file is part of ts_standardscripts
#
# Developed for the LSST Telescope and Site Systems.
# This product includes software developed by the LSST Project
# (https://www.lsst.org).
# See the COPYRIGHT file at the top-level directory of this distribution
# for details of code ownership.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

"""
Sphinx extension to generate a categorized list of Standard Scripts.

This extension creates a directive `script-categorizer` that
generates a categorized list of all Standard Scripts by extracting
information from the script class docstrings and outputting standard RST
for better integration with Sphinx navigation.
"""

import argparse
import asyncio
import importlib.util
import inspect
import logging
import os
import re
import sys
import traceback
from pathlib import Path

import yaml
from docutils import nodes
from sphinx.util.docutils import SphinxDirective

logger = logging.getLogger(__name__)
logger_level = logging.INFO
logger.setLevel(logger_level)


def setup(app):
    """Set up the Sphinx extension."""
    app.add_directive("script-categorizer", ScriptCategorizer)
    return {
        "version": "0.1",
        "parallel_read_safe": True,
        "parallel_write_safe": True,
    }


class ScriptCategorizer(SphinxDirective):
    """A directive that generates a categorized list of Standard Scripts
    as RST text."""

    has_content = False
    required_arguments = 0
    optional_arguments = 0

    def run(self):
        """Generate the script list as RST text."""
        try:
            try:
                scripts_dir = (
                    Path(__file__).parent.parent
                    / "python"
                    / "lsst"
                    / "ts"
                    / "standardscripts"
                    / "data"
                    / "scripts"
                )
                if not scripts_dir.exists():
                    error = nodes.error()
                    error += nodes.paragraph(
                        text=f"Error: Scripts directory not found at {scripts_dir}"
                    )
                    return [error]
            except Exception as e:
                error = nodes.error()
                error += nodes.paragraph(
                    text=f"Error: Could not find scripts directory: {str(e)}"
                )
                return [error]

            categories = {
                "Main Telescope": {},
                "Auxiliary Telescope": {},
                "OCS": {},
                "System": {},
                "Other": {},
            }

            category_mapping = {
                "ocs": "OCS",
                "maintel": "Main Telescope",
                "auxtel": "Auxiliary Telescope",
                "system": "System",
                "common": "System",
            }

            # Human-friendly root labels for path-like headers
            root_label_map = {
                "Main Telescope": "Maintel",
                "Auxiliary Telescope": "Auxtel",
                "OCS": "OCS",
                "System": "System",
                "Other": "Other",
            }

            # Setup mocking to prevent script execution
            original_argv = sys.argv.copy()
            original_argparse = sys.modules.get("argparse", None)
            original_exit = sys.exit
            original_asyncio_run = asyncio.run

            def mock_exit(code=None):
                logger.debug(f"Mock sys.exit called with code {code}")
                return None

            sys.exit = mock_exit

            def mock_asyncio_run(coro):
                logger.debug(f"Mock asyncio.run called with {coro}")
                return None

            asyncio.run = mock_asyncio_run

            class MockArgParse:
                class Namespace:
                    def __init__(self, **kwargs):
                        for key, value in kwargs.items():
                            setattr(self, key, value)

                class Action:
                    def __init__(self, **kwargs):
                        for key, value in kwargs.items():
                            setattr(self, key, value)

                def ArgumentParser(self, *args, **kwargs):
                    class MockParser:
                        def add_argument(self, *args, **kwargs):
                            pass

                        def parse_args(self, args=None):
                            return argparse.Namespace()

                        def add_mutually_exclusive_group(self, *args, **kwargs):
                            return self

                        def add_argument_group(self, *args, **kwargs):
                            return self

                        def print_help(self, *args, **kwargs):
                            pass

                        def print_usage(self, *args, **kwargs):
                            pass

                    return MockParser()

            sys.modules["argparse"] = MockArgParse()

            sys.argv = [sys.argv[0]]
            os.environ["LSST_TOPIC_SUBNAME"] = "test"

            try:
                script_files = []
                for root, dirs, files in os.walk(scripts_dir):
                    for file in files:
                        if (
                            not file.endswith(".py")
                            or file == "__init__.py"
                            or file == "README.md"
                        ):
                            continue
                        script_files.append(Path(root) / file)

                logger.info(f"Found {len(script_files)} script files")

                for file_path in sorted(script_files):
                    logger.info(f"Processing file: {file_path}")

                    try:
                        # Import the module
                        module_name = file_path.stem
                        spec = importlib.util.spec_from_file_location(
                            module_name, str(file_path)
                        )
                        if spec is None or spec.loader is None:
                            logger.warning(f"Could not create spec for {file_path}")
                            continue

                        module = importlib.util.module_from_spec(spec)
                        sys.modules[module_name] = module

                        logger.debug(f"import dir(module): {dir(module)}")

                        regex_amain_class_name = None

                        # Try to detect if this file has an amain call
                        try:
                            with open(str(file_path), "r") as f:
                                script_content = f.read()

                            amain_pattern = (
                                r"^[^#]*asyncio\.run\s*\(\s*(\w+)\.amain\s*\("
                            )
                            amain_matches = re.findall(
                                amain_pattern, script_content, re.MULTILINE
                            )

                            if amain_matches:
                                regex_amain_class_name = amain_matches[0]
                                logger.debug(
                                    f"Found amain call for class: {regex_amain_class_name}"
                                )
                        except Exception as e:
                            logger.warning(f"Error checking for amain call: {str(e)}")

                        # To get the class info execute the module while
                        # catching any exceptions
                        try:
                            spec.loader.exec_module(module)
                        except Exception as e:
                            logger.warning(
                                f"Error executing module {file_path}: {str(e)}"
                            )
                            # Continue anyway - we can still extract class info
                            pass

                        # Reset logger level as the execution of the module
                        # may have changed it
                        logger.setLevel(logger_level)

                        logger.debug(f"exec dir(module): {dir(module)}")

                        script_class = None
                        amain_classes = []

                        class_module_paths = {}
                        for attr_name in dir(module):
                            if attr_name.startswith("_"):
                                continue
                            try:
                                attr = getattr(module, attr_name)
                                logger.debug(f"attr: {attr}")
                                if inspect.isclass(attr) and hasattr(attr, "amain"):
                                    amain_classes.append(attr)

                                    full_module_path = attr.__module__
                                    class_name = attr.__name__

                                    if not full_module_path.startswith("lsst."):

                                        path_str = str(file_path)
                                        lsst_index = path_str.find("/lsst/")

                                        if lsst_index >= 0:
                                            base_path = path_str[
                                                lsst_index + 1 :
                                            ]  # +1 to skip the leading '/'
                                            base_path = base_path.replace(
                                                "/", "."
                                            ).replace(".py", "")
                                            rel_module = full_module_path
                                            full_module_path = base_path
                                            logger.debug(
                                                f"Converted relative path '{rel_module}' to absolute: "
                                                f"{full_module_path}"
                                            )
                                        else:
                                            logger.error(
                                                f"Error: Could not find 'lsst' in path '{path_str}'"
                                            )

                                            rel_path = file_path.relative_to(
                                                scripts_dir
                                            )
                                            rel_path_str = (
                                                str(rel_path)
                                                .replace(".py", "")
                                                .replace("/", ".")
                                            )
                                            full_module_path = (
                                                f"MODULE_ERROR.{rel_path_str}"
                                            )

                                    class_module_paths[class_name] = full_module_path
                                    logger.debug(
                                        f"Found class with amain: {class_name}, "
                                        f"module path: {full_module_path}"
                                    )
                            except Exception as e:
                                logger.warning(
                                    f"Error accessing attribute {attr_name}: {str(e)}"
                                )
                                continue

                        # Select the appropriate class
                        if amain_classes:
                            if regex_amain_class_name:
                                for cls in amain_classes:
                                    if cls.__name__ == regex_amain_class_name:
                                        script_class = cls
                                        logger.debug(
                                            f"Found class used in amain call: {regex_amain_class_name}"
                                        )
                                        break

                        if script_class is None:
                            logger.warning(f"No script class found in {file_path}")
                            continue

                        script_class_name = script_class.__name__
                        docstring = inspect.getdoc(script_class) or ""

                        logger.debug(f"docstring: {docstring}")

                        # Determine category and subcategory from file path
                        rel_path = file_path.relative_to(scripts_dir)
                        path_parts = rel_path.parts
                        str_path = str(rel_path)

                        # Determine category
                        # Default to "Other" if we can't determine a category
                        category = "Other"
                        if len(path_parts) >= 1:
                            top_dir = path_parts[0]

                            if top_dir in category_mapping:
                                category = category_mapping[top_dir]
                            elif any(
                                key in str_path.lower() for key in category_mapping
                            ):
                                for key, value in category_mapping.items():
                                    if key in str_path.lower():
                                        category = value
                                        break

                        logger.debug(f"category: {category}")

                        # Determine subcategory
                        subcategory = None
                        # Only treat a real second-level directory as a
                        # subcategory.
                        # Examples:
                        #   maintel/foo.py -> subcategory None (category-level)
                        #   maintel/scheduler/bar.py -> subcategory 'Scheduler'
                        #   auxtel/atdome/close.py -> subcategory 'Atdome'
                        if len(path_parts) >= 3:
                            second = path_parts[1]
                            # second must be a directory name (the third part
                            # is the file)
                            if not second.endswith(".py"):
                                subcategory = (
                                    second.capitalize()
                                    if second != "scheduler"
                                    else "Scheduler"
                                )
                        logger.debug(
                            f"rel_path: {rel_path} -> subcategory: {subcategory}"
                        )

                        if "scripts" not in categories[category]:
                            categories[category]["scripts"] = []

                        if subcategory is None:
                            categories[category]["scripts"].append(
                                (
                                    script_class_name,
                                    script_class,
                                    docstring,
                                    str(rel_path),
                                    class_module_paths,
                                )
                            )
                            logger.debug(
                                f"1Added name: {script_class_name} class: {script_class} "
                                f"path: {rel_path} mods: {class_module_paths} to {category}/{subcategory}"
                            )
                        else:
                            if subcategory not in categories[category]:
                                categories[category][subcategory] = []
                            categories[category][subcategory].append(
                                (
                                    script_class_name,
                                    script_class,
                                    docstring,
                                    str(rel_path),
                                    class_module_paths,
                                )
                            )
                            logger.debug(
                                f"2Added name: {script_class_name} class: {script_class} "
                                f"path: {rel_path} mods: {class_module_paths} to {category}/{subcategory}"
                            )
                    except Exception as e:
                        logger.error(f"Error processing {file_path}: {str(e)}")
                        logger.error(traceback.format_exc())
                        continue

            finally:
                # Restore original state
                sys.argv = original_argv
                if original_argparse:
                    sys.modules["argparse"] = original_argparse
                sys.exit = original_exit
                asyncio.run = original_asyncio_run

            rst_lines = []

            # Add a table of contents section
            rst_lines.append(".. _script-categories:")
            rst_lines.append("")
            rst_lines.append("Script Categories")
            rst_lines.append("=================")
            rst_lines.append("")

            rst_lines.append(".. contents::")
            rst_lines.append("   :local:")
            rst_lines.append("   :depth: 3")
            rst_lines.append("")

            # Add custom CSS for better TOC formatting
            rst_lines.append(".. raw:: html")
            rst_lines.append("")
            rst_lines.append("   <style>")
            rst_lines.append("     .contents ul ul {")
            rst_lines.append("       margin-left: 2em !important;")
            rst_lines.append("     }")
            rst_lines.append("     .contents > ul > li {")
            rst_lines.append("       font-weight: bold;")
            rst_lines.append("     }")
            rst_lines.append("     .contents ul ul > li {")
            rst_lines.append("       font-weight: normal;")
            rst_lines.append("     }")
            rst_lines.append("     details.schema-details {")
            rst_lines.append("       margin-top: 0.25rem;")
            rst_lines.append("       margin-bottom: 0.75rem;")
            rst_lines.append("     }")
            rst_lines.append("     details.schema-details > summary {")
            rst_lines.append("       display: none;")
            rst_lines.append("     }")
            rst_lines.append("     /* Inline 'Show Schema' link styling */")
            rst_lines.append('     li a[href^="#schema-"] {')
            rst_lines.append("       color: #0366d6; /* theme blue */")
            rst_lines.append("       font-size: 0.95em;")
            rst_lines.append("       margin-left: 0.35rem;")
            rst_lines.append("       text-decoration: none;")
            rst_lines.append("     }")
            rst_lines.append('     li a[href^="#schema-"]:hover {')
            rst_lines.append("       color: #024ea2; /* darker on hover */")
            rst_lines.append("       text-decoration: underline;")
            rst_lines.append("     }")
            rst_lines.append(
                "     /* Make class name links match 'Show Schema' styling */"
            )
            rst_lines.append("     li a.reference.internal {")
            rst_lines.append("       color: #0366d6 !important;")
            rst_lines.append("       font-size: 0.95em !important;")
            rst_lines.append("       text-decoration: none !important;")
            rst_lines.append("     }")
            rst_lines.append("     li a.reference.internal:hover {")
            rst_lines.append("       color: #024ea2 !important;")
            rst_lines.append("       text-decoration: underline !important;")
            rst_lines.append("     }")
            rst_lines.append(
                "     li a.reference.internal > code.xref.py.py-class.docutils.literal.notranslate {"
            )
            rst_lines.append("       color: #0366d6 !important;")
            rst_lines.append("       font-family: inherit !important;")
            rst_lines.append("       font-weight: normal !important;")
            rst_lines.append("       font-size: 0.95em !important;")
            rst_lines.append("       background: transparent !important;")
            rst_lines.append(
                "       padding: 0 !important; border: 0 !important; box-shadow: none !important;"
            )
            rst_lines.append("     }")
            rst_lines.append(
                "     li a.reference.internal:hover > code.xref.py.py-class.docutils.literal.notranslate {"
            )
            rst_lines.append("       color: #024ea2 !important;")
            rst_lines.append("       text-decoration: underline !important;")
            rst_lines.append("     }")
            rst_lines.append("   </style>")
            rst_lines.append("")
            # JS: toggle schema <details> when inline (Schema) link is clicked
            rst_lines.append(".. raw:: html")
            rst_lines.append("")
            rst_lines.append("   <script>")
            rst_lines.append(
                "     document.addEventListener('DOMContentLoaded', function () {"
            )
            rst_lines.append(
                "       document.querySelectorAll('a[href^=\"#schema-\"]').forEach(function(a){"
            )
            rst_lines.append("         a.addEventListener('click', function (ev) {")
            rst_lines.append("           var id = a.getAttribute('href').slice(1);")
            rst_lines.append("           var el = document.getElementById(id);")
            rst_lines.append(
                "           if (el && el.tagName.toLowerCase() === 'details') {"
            )
            rst_lines.append("             ev.preventDefault(); ev.stopPropagation();")
            rst_lines.append("             el.open = !el.open;")
            rst_lines.append("           }")
            rst_lines.append("         });")
            rst_lines.append("       });")
            rst_lines.append("     });")
            rst_lines.append("   </script>")
            rst_lines.append("")

            rst_lines.append("Script Category Index")
            rst_lines.append("---------------------")
            rst_lines.append("")

            # First level - categories
            for category, collections in categories.items():
                if not collections:
                    continue

                category_id = f"script-category-{category.lower().replace(' ', '-')}"
                rst_lines.append(f"* :ref:`{category} Scripts <{category_id}>`")

                # Root (category-level) scripts entry first (if any)
                if "scripts" in collections and collections["scripts"]:
                    root_label = root_label_map.get(category, category)
                    root_sub_id = (
                        f"script-subcategory-{category.lower().replace(' ', '-')}-root"
                    )
                    rst_lines.append(f"  * :ref:`{root_label} <{root_sub_id}>`")

                # Then the real subfolders, sorted alphabetically
                sorted_subcats = sorted(
                    [k for k in collections.keys() if k != "scripts"]
                )
                for subcategory in sorted_subcats:
                    if not collections[subcategory]:
                        continue

                    subcategory_id = (
                        f"script-subcategory-{category.lower().replace(' ', '-')}-"
                        f"{subcategory.lower().replace(' ', '-')}"
                    )
                    root_label = root_label_map.get(category, category)
                    path_like = f"{root_label}/{subcategory.replace('_', ' ').title()}"
                    rst_lines.append(f"  * :ref:`{path_like} <{subcategory_id}>`")

            rst_lines.append("")
            rst_lines.append("----")
            rst_lines.append("")

            # Add each category and its scripts
            for category, collections in categories.items():
                if not collections:
                    continue

                # Category header (level 2)
                category_id = f"script-category-{category.lower().replace(' ', '-')}"
                rst_lines.append(f".. _{category_id}:")
                rst_lines.append("")
                rst_lines.append(f"{category} Scripts")
                rst_lines.append("=" * len(f"{category} Scripts"))
                rst_lines.append("")

                # Show root (category-level) scripts first
                if "scripts" in collections and collections["scripts"]:
                    root_label = root_label_map.get(category, category)
                    root_sub_header = f"{root_label}"
                    root_sub_id = (
                        f"script-subcategory-{category.lower().replace(' ', '-')}-root"
                    )
                    rst_lines.append(f".. _{root_sub_id}:")
                    rst_lines.append("")
                    rst_lines.append(root_sub_header)
                    rst_lines.append("-" * len(root_sub_header))
                    rst_lines.append("")

                    for (
                        script_class_name,
                        script_class,
                        docstring,
                        rel_path,
                        class_module_paths,
                    ) in sorted(collections["scripts"], key=lambda x: x[0]):
                        script_name = Path(rel_path).name

                        module_path = class_module_paths.get(
                            script_class_name,
                            f"MODULE_ERROR.{str(rel_path).replace('.py', '').replace('/', '.')}",
                        )

                        # Extract one-paragraph summary from docstring
                        first_para = ""
                        if docstring:
                            lines = docstring.split("\n")
                            first_para_lines = []
                            for line in lines:
                                line = line.strip()
                                if not line and first_para_lines:
                                    break
                                if line:
                                    first_para_lines.append(line)
                            if first_para_lines:
                                first_para = " ".join(first_para_lines)

                        # Create schema id; compute schema text (if any)
                        schema_id = "schema-" + str(rel_path).lower().replace(
                            "/", "-"
                        ).replace("_", "-").replace(".", "-")
                        schema_yaml = None
                        try:
                            if hasattr(script_class, "get_schema") and callable(
                                getattr(script_class, "get_schema")
                            ):
                                schema_obj = script_class.get_schema()  # type: ignore[attr-defined]
                                if schema_obj is not None:
                                    if isinstance(schema_obj, (dict, list)):
                                        schema_yaml = yaml.safe_dump(
                                            schema_obj,
                                            sort_keys=True,
                                            default_flow_style=False,
                                        )
                                    elif isinstance(schema_obj, str):
                                        try:
                                            parsed = yaml.safe_load(schema_obj)
                                            if isinstance(parsed, (dict, list)):
                                                schema_yaml = yaml.safe_dump(
                                                    parsed,
                                                    sort_keys=True,
                                                    default_flow_style=False,
                                                )
                                            else:
                                                schema_yaml = schema_obj
                                        except Exception:
                                            schema_yaml = schema_obj
                                    else:
                                        schema_yaml = yaml.safe_dump(
                                            schema_obj,
                                            sort_keys=True,
                                            default_flow_style=False,
                                        )
                        except Exception as e:
                            logger.warning(
                                f"Failed to get schema for {script_name}: {e}"
                            )

                        # Build list entry
                        # include inline link only if a schema was found
                        entry_line = f"* **{script_name}** "
                        if schema_yaml:
                            entry_line += f"`Show Schema <#{schema_id}>`_ "
                        entry_line += (
                            f"(:py:class:`{script_class_name} <"
                            f"{module_path}.{script_class_name}>`)"
                        )
                        if first_para:
                            entry_line += f" - {first_para}"

                        rst_lines.append(entry_line)
                        rst_lines.append("")

                        if schema_yaml:
                            rst_lines.append("  .. raw:: html")
                            rst_lines.append("")
                            rst_lines.append(
                                f'     <details id="{schema_id}" class="schema-details">'
                            )
                            rst_lines.append("     <summary></summary>")
                            rst_lines.append("")

                            rst_lines.append("  .. code-block:: yaml")
                            rst_lines.append("")
                            for line in schema_yaml.rstrip().splitlines():
                                rst_lines.append(f"     {line}")
                            rst_lines.append("")

                            rst_lines.append("  .. raw:: html")
                            rst_lines.append("")
                            rst_lines.append("     </details>")
                            rst_lines.append("")

                # Then subcategories (folders), sorted alphabetically
                sorted_subcategories = sorted(
                    [k for k in collections.keys() if k != "scripts"]
                )

                for subcategory in sorted_subcategories:
                    items = collections[subcategory]
                    if not items:
                        continue

                    subcategory_id = (
                        f"script-subcategory-{category.lower().replace(' ', '-')}-"
                        f"{subcategory.lower().replace(' ', '-')}"
                    )
                    rst_lines.append(f".. _{subcategory_id}:")
                    rst_lines.append("")
                    root_label = root_label_map.get(category, category)
                    path_like_header = (
                        f"{root_label}/{subcategory.replace('_', ' ').title()}"
                    )
                    rst_lines.append(path_like_header)
                    rst_lines.append("-" * len(path_like_header))
                    rst_lines.append("")

                    for (
                        script_class_name,
                        script_class,
                        docstring,
                        rel_path,
                        class_module_paths,
                    ) in sorted(items, key=lambda x: x[0]):
                        script_name = Path(rel_path).name

                        module_path = class_module_paths.get(
                            script_class_name,
                            f"MODULE_ERROR.{str(rel_path).replace('.py', '').replace('/', '.')}",
                        )

                        # Extract one-paragraph summary
                        first_para = ""
                        if docstring:
                            lines = docstring.split("\n")
                            first_para_lines = []
                            for line in lines:
                                line = line.strip()
                                if not line and first_para_lines:
                                    break
                                if line:
                                    first_para_lines.append(line)
                            if first_para_lines:
                                first_para = " ".join(first_para_lines)

                        schema_id = "schema-" + str(rel_path).lower().replace(
                            "/", "-"
                        ).replace("_", "-").replace(".", "-")

                        schema_yaml = None
                        try:
                            if hasattr(script_class, "get_schema") and callable(
                                getattr(script_class, "get_schema")
                            ):
                                schema_obj = script_class.get_schema()  # type: ignore[attr-defined]
                                if schema_obj is not None:
                                    if isinstance(schema_obj, (dict, list)):
                                        schema_yaml = yaml.safe_dump(
                                            schema_obj,
                                            sort_keys=True,
                                            default_flow_style=False,
                                        )
                                    elif isinstance(schema_obj, str):
                                        try:
                                            parsed = yaml.safe_load(schema_obj)
                                            if isinstance(parsed, (dict, list)):
                                                schema_yaml = yaml.safe_dump(
                                                    parsed,
                                                    sort_keys=True,
                                                    default_flow_style=False,
                                                )
                                            else:
                                                schema_yaml = schema_obj
                                        except Exception:
                                            schema_yaml = schema_obj
                                    else:
                                        schema_yaml = yaml.safe_dump(
                                            schema_obj,
                                            sort_keys=True,
                                            default_flow_style=False,
                                        )
                        except Exception as e:
                            logger.warning(
                                f"Failed to get schema for {script_name}: {e}"
                            )

                        entry_line = f"* **{script_name}** "
                        if schema_yaml:
                            entry_line += f"`Show Schema <#{schema_id}>`_ "
                        entry_line += (
                            f"(:py:class:`{script_class_name} <"
                            f"{module_path}.{script_class_name}>`)"
                        )
                        if first_para:
                            entry_line += f" - {first_para}"
                        rst_lines.append(entry_line)
                        rst_lines.append("")

                        if schema_yaml:
                            rst_lines.append("  .. raw:: html")
                            rst_lines.append("")
                            rst_lines.append(
                                f'     <details id="{schema_id}" class="schema-details">'
                            )
                            rst_lines.append("     <summary></summary>")
                            rst_lines.append("")

                            rst_lines.append("  .. code-block:: yaml")
                            rst_lines.append("")
                            for line in schema_yaml.rstrip().splitlines():
                                rst_lines.append(f"     {line}")
                            rst_lines.append("")

                            rst_lines.append("  .. raw:: html")
                            rst_lines.append("")
                            rst_lines.append("     </details>")
                            rst_lines.append("")

            if not any(
                any(subcat for subcat in cat.values()) for cat in categories.values()
            ):
                text = "No scripts were found in the scripts directory."
                warning = nodes.warning()
                warning += nodes.paragraph(text)
                logger.warning(text)
                return [warning]

            logger.info("Generated RST documentation for scripts")
            logger.info(
                "Number of categories with scripts: "
                f"{sum(1 for subcats in categories.values() if any(subcats))}"
            )
            logger.info(
                "Total number of scripts: "
                f"{sum(len(items) for subcats in categories.values() for items in subcats.values())}"
            )

            rst_content = "\n".join(rst_lines)

            # Let Sphinx parse the RST text
            # as if it were part of the original document.
            self.state_machine.insert_input(rst_content.splitlines(), "")

            # Return an empty node list as we've already inserted
            # the doc content
            return []

        except Exception as e:
            logger.error(f"Error in script categorizer: {str(e)}")
            logger.error(traceback.format_exc())
            error = nodes.error()
            error += nodes.paragraph(text=f"Error in script categorizer: {str(e)}")
            return [error]
