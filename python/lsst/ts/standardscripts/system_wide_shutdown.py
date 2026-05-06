# This file is part of ts_standardscripts.
#
# Developed for the Vera C. Rubin Observatory Telescope and Site Systems.
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

__all__ = ["SystemWideShutdown"]

import asyncio
import types
import typing

import yaml
from lsst.ts import salobj, xml
from lsst.ts.standardscripts.utils import find_running_instances
from lsst.ts.xml.component_info import ComponentInfo


class SystemWideShutdown(salobj.BaseScript):
    """Discover all running CSCs and send them all to OFFLINE state.

    Notes
    -----

    This SAL Script works by getting a list of components from the IDL
    directory, then finds which components are running by listening in to
    heartbeats. For indexed components, the script will accumulate indices
    until it receives at least 3 heartbeats from 1 of the components. This
    gives enough time to find all running instances of a particular CSC.

    After discovering the runnings CSCs, and their indices, the Script attempts
    to send them all to OFFLINE. The user can control the order in which the
    shutdown happens by providing the names of the components to start with and
    to end with. In any case, the Script will always finish with the
    ScriptQueue and ignore Scripts. Users can also provide a list of CSCs to be
    ignored.

    In order to prevent accidental execution of this Script, users must provide
    two required configuration parameters; user and reason. This also helps
    keep track of who is executing the shutdown and why.
    """

    def __init__(self, index: int) -> None:
        super().__init__(index=index, descr="Send all CSCs to OFFLINE.")

        self.failed: dict[str, str] = dict()
        self.components_to_ignore = ["Script", "ScriptQueue"]
        self.components_to_end_with = ["ScriptQueue"]

        self._max_concurrency = 10
        self._concurrent_capacity = asyncio.Semaphore(self._max_concurrency)

    @classmethod
    def get_schema(cls) -> None | dict[str, typing.Any]:
        schema_yaml = """
$schema: http://json-schema.org/draft-07/schema#
$id: https://github.com/lsst-ts/ts_standardscripts/python/lsst/ts/standardscripts/system_wide_shutdown.py
title: SystemWideShutdown v1
description: Configuration for SystemWideShutdown script.
type: object
properties:
    user:
        description: Name of the user that is executing the script.
        type: string
    reason:
        description: Reason for running the system wide shutdown.
        type: string
    ignore:
        description: >
            CSCs to ignore. Can specify a whole CSC (e.g., "Test") or an
            indexed CSC (e.g., "Test:1"). Requesting a whole CSC and an
            indexed CSC of the same type will cause the script to fail.
            Adding an index to a non-indexed CSC will also cause the
            script to fail. Ignoring a CSC[:index] that is not running,
            is a no-op. If the index is mistyped (e.g. "Test:a") the
            request is skipped.
        type: array
        items:
            type: string
        default: []
    start_with:
        description: CSCs to start with.
        type: array
        items:
            type: string
        default: []
    end_with:
        description: CSCs to end with.
        type: array
        items:
            type: string
        default: []
required: [user, reason]
additionalProperties: false
        """
        return yaml.safe_load(schema_yaml)

    async def configure(self, config: types.SimpleNamespace) -> None:
        self.config = config

    def set_metadata(self, metadata: salobj.type_hints.BaseMsgType) -> None:
        metadata.duration = 60.0

    async def run(self) -> None:
        await self.check_ignored_components()

        components_running = await self.discover_components()

        self.log.info(
            f"Shutting down {len(components_running)} components as requested by {self.config.user}. "
            f"Reason: {self.config.reason}"
        )

        await self.checkpoint(
            f"Shutdown :: Requested by {self.config.user}. "
            f"Reason: {self.config.reason}. "
            f"Found {len(components_running)} running components."
        )

        for component in self.config.ignore:
            if ":" in component:
                component_name, index_str = component.rsplit(":", 1)
                try:
                    index = int(index_str)
                except ValueError:
                    self.log.warning(
                        f"Invalid index '{index_str}' in ignore list: {component}. "
                        "Skipping."
                    )
                    continue
                if component_name in components_running:
                    if index in components_running[component_name]:
                        self.log.debug(
                            f"Excluding {component_name}:{index} from the list."
                        )
                        components_running[component_name].remove(index)
                        if not components_running[component_name]:
                            del components_running[component_name]
            elif component in components_running:
                self.log.debug(f"Excluding {component} from the list.")
                components_running.pop(component)

        await self.checkpoint("Shutdown :: Start with components.")
        for component in self.config.start_with:
            if component in components_running:
                component_indices = components_running.pop(component)
                await self.shutdown(component, component_indices)

        await self.checkpoint("Shutdown :: Running components.")
        for component in components_running:
            if component not in self.config.end_with:
                component_indices = components_running[component]
                await self.shutdown(component, component_indices)

        await self.checkpoint("Shutdown :: End with components.")
        for component in self.config.end_with:
            if component in components_running:
                component_indices = components_running.pop(component)
                await self.shutdown(component, component_indices)

        for component in self.components_to_end_with:
            if component in components_running:
                component_indices = components_running.pop(component)
                await self.shutdown(component, component_indices)

        if len(self.failed) > 0:
            error_message = (
                "The following components failed to transition to offline:\n"
            )

            for component in self.failed:
                error_message += f"{component}::{self.failed[component]}\n"

            self.log.error(error_message)
            raise RuntimeError(
                f"A total of {len(self.failed)} components failed to transition to offline."
            )

    async def check_ignored_components(self) -> None:
        """Validate the ignore configuration.

        Ensures that:
        - Indexed components are only specified with a valid index
        - Non-indexed components are not specified with an index
        - A component is not specified both with and without an index

        Raises
        ------
        ValueError
            If the ignore configuration is invalid.
        """
        indexed_full = set()
        indexed_specific = set()
        non_indexed_components = set()
        invalid_index = set()
        non_indexed_with_index = set()

        for component in self.config.ignore:
            if ":" in component:
                component_name, index_str = component.rsplit(":", 1)
                try:
                    int(index_str)
                except ValueError:
                    invalid_index.add(component)

                component_info = ComponentInfo(component_name, "sal")
                if not component_info.indexed:
                    non_indexed_with_index.add(component)

                indexed_specific.add(component_name)
            else:
                component_info = ComponentInfo(component, "sal")
                if component_info.indexed:
                    indexed_full.add(component)
                else:
                    non_indexed_components.add(component)

        errors = []

        if invalid_index:
            invalid_index_str = ",".join(invalid_index)
            errors.append(
                f"The following components indexes are invalid: {invalid_index_str}. "
                "Indices must be integers."
            )

        if non_indexed_with_index:
            non_indexed_with_index_str = ",".join(non_indexed_with_index)
            errors.append(
                f"The following components are not indexed: {non_indexed_with_index_str}. "
                "Make sure non-indexed components are not requiring index."
            )

        conflicts = indexed_full & indexed_specific

        if conflicts:
            conflict_list = ", ".join(conflicts)
            errors.append(
                f"Cannot ignore both all instances and specific indices for "
                f"the same component: {conflict_list}. "
                f"Remove either '{conflict_list}' or '{conflict_list}:N' from the ignore list."
            )

        if errors:
            error_message = "\n".join(errors)
            raise RuntimeError(
                f"Found {len(errors)} with the requested components to ignore:\n{error_message}"
            )

    async def discover_components(self) -> dict[str, list[int]]:
        """Discover components running in the system.

        Returns
        -------
        dict[str, list[int]]
            Dictionary with the name of the component as key and list of
            indices as values.
        """

        components_running: dict[str, list[int]] = dict()

        components = self._get_all_components()

        task_find_running_instances = [
            asyncio.create_task(find_running_instances(self.domain, component))
            for component in components
        ]

        for task in asyncio.as_completed(task_find_running_instances):
            component, component_indices = await task
            if component_indices:
                components_running[component] = component_indices

        return components_running

    def _get_all_components(self) -> list[str]:
        """Get the name of all components in the system.

        Returns
        -------
        list[str]
            Name of all components in the system.
        """

        components: list[str] = xml.subsystems.copy()

        for component in self.components_to_ignore:
            if component in components:
                components.remove(component)

        return components

    async def shutdown(self, component: str, indices: list[int]) -> None:
        """Shutdown component with given indices.

        Parameters
        ----------
        component : str
            Name of the component.
        indices : list[int]
            List of indices.
        """

        for index in indices:
            self.log.info(f"Shutdown {component}:{index}.")
            async with salobj.Remote(
                self.domain, component, index=index, include=["summaryState"]
            ) as remote:
                try:
                    await salobj.set_summary_state(remote, salobj.State.OFFLINE)
                except Exception as e:
                    self.log.debug(f"Failed to shutdown {component}:{index}::{e}")
                    self.failed[f"{component}:{index}"] = f"{e}"
                else:
                    self.log.debug(f"{component}:{index} offline.")
