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
# along with this program. If not, see <https://www.gnu.org/licenses/>.

__all__ = ["SetSummaryState"]

import asyncio

import yaml
from lsst.ts import salobj

try:
    from lsst.ts.salobj import WildcardIndexError, name_to_name_index
except ImportError:
    # If not available in ts_salobj, use the local fallback from utils
    from lsst.ts.standardscripts.utils import name_to_name_index, WildcardIndexError

from lsst.ts.standardscripts.utils import find_running_instances


class SetSummaryState(salobj.BaseScript):
    """Set the summary state for one or more CSCs.

    Notes
    -----
    **Checkpoints**

    * "set {csc_name}:{index}" before commanding a CSC.

    **Details**

    * Takes the shortest path from the current state to the requested state.
      Thus if you want to configure a CSC you should specify it twice:

      * First with state "STANDBY".
      * Next with state "DISABLED" or "ENABLED" and the desired override.

    * Dynamically loads IDL files as needed.
    """

    def __init__(self, index):
        super().__init__(index=index, descr="Put CSCs into specified states")

        self.valid_transitions = ["start", "enable", "disable", "standby"]

        # approximate time to construct a Remote for a CSC (sec)
        self.create_remote_time = 15
        # time limit for each state transition command (sec);
        # make it generous enough to handle any CSC
        self.cmd_timeout = 10

    @classmethod
    def get_schema(cls):
        schema_yaml = """
            $schema: http://json-schema.org/draft-07/schema#
            $id: https://github.com/lsst-ts/ts_standardscripts/SetSummaryState.yaml
            title: SetSummaryState v1
            description: Configuration for SetSummaryState
            type: object
            properties:
              data:
                description: List of (CSC_name[:index], state_name [, override_to_apply]);
                    the default index is 0;
                    the default override_to_apply is ""
                    If the index is '*', the script will discover all running instances.
                type: array
                minItems: 1
                items:
                    type: array
                    minItems: 2
                    maxItems: 3
                    items:
                        type: string
            required: [data]
            additionalProperties: false
        """
        return yaml.safe_load(schema_yaml)

    async def configure(self, config):
        """Configure the script.

        Specify the CSCs to command, and for each CSC,
        specify the desired summary state optionally the override.

        Parameters
        ----------
        config : `types.SimpleNamespace`
            Configuration with one attribute:

            * data : a list, where each element is a tuple
              with two or three entries:

                * CSC name and optional index as ``csc_name:index`` (a `str`).
                  For a CSC that is not indexed you may omit ``:index``
                  or specify ``:0``, as you prefer.
                * Name of desired summary state, case blind, e.g. "enabled"
                  or "STANDBY". The "fault" state is not supported.
                * The value of ``configurationOverride`` in the ``start``
                  command for each CSC. Ignored unless the ``start`` command
                  is issued (i.e. the CSC transitions from "STANDBY" to
                  "DISABLED"). If omitted then "" is used.

        Notes
        -----
        Saves the results as two attributes:

        * ``nameind_state_override``: a list, each element of which is a tuple
          with three elements:

            * (csc_name, index)
            * desired summary state, as an `lsst.ts.salobj.State`
            * override, or "" if none specified

        * remotes: a dict of (csc_name, index): remote,
          an `lsst.ts.salobj.Remote`

        Constructing a `salobj.Remote` is slow (DM-17904), so configuration
        may take a 10s or 100s of seconds per CSC.
        """
        self.log.info("Configure started")

        # parse the data
        nameind_state_override = []
        for elt in config.data:

            try:
                # Try to parse the name and index
                name, index = name_to_name_index(elt[0])
            except WildcardIndexError as e:
                name = e.name
                index = "*"  # Mark as wildcard

            state_name = elt[1]
            if not isinstance(state_name, str):
                raise ValueError(f"{elt} summary state {state_name!r} is not a string")
            try:
                state = getattr(salobj.State, state_name.upper())
            except AttributeError:
                raise ValueError(f"{elt} has unknown summary state {state_name!r}")
            if state == salobj.State.FAULT:
                raise ValueError(f"{elt} state cannot be FAULT")
            if len(elt) == 3:
                override = elt[2]
                if not isinstance(override, str):
                    raise ValueError(f"{elt} override {override!r} is not a string")
            else:
                override = ""

            # If wildcard index is used, enter discovery mode
            if index == "*":
                component, discovered_indices = await find_running_instances(
                    self.domain, name
                )

                for idx in discovered_indices:
                    nameind_state_override.append(((name, idx), state, override))
            else:
                nameind_state_override.append(((name, index), state, override))

        # construct remotes
        remotes = dict()
        for elt in nameind_state_override:
            name_index = elt[0]
            name, index = name_index
            self.log.debug(f"Create remote {name}:{index}")
            if name_index not in remotes:
                remote = salobj.Remote(
                    domain=self.domain, name=name, index=index, include=["summaryState"]
                )
                remotes[name_index] = remote

        self.nameind_state_override = nameind_state_override
        self.remotes = remotes

    def set_metadata(self, metadata):
        """Compute estimated duration.

        Parameters
        ----------
        metadata : SAPY_Script.Script_logevent_metadataC
        """
        # a crude estimate; state transitions are typically quick
        # but we don't know how many of them there will be
        metadata.duration = len(self.nameind_state_override) * 2

    async def run(self):
        """Run script."""
        tasks = [
            remote.start_task
            for remote in self.remotes.values()
            if not remote.start_task.done()
        ]
        if tasks:
            self.log.info(f"Waiting for {len(tasks)} remotes to be ready")
            await asyncio.gather(*tasks)

        for name_index, state, override in self.nameind_state_override:
            name, index = name_index
            await self.checkpoint(f"set {name}:{index}")
            remote = self.remotes[(name, index)]
            await salobj.set_summary_state(
                remote=remote, state=state, override=override, timeout=self.cmd_timeout
            )
