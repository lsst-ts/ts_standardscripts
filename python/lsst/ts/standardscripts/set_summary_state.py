# This file is part of ts_standardscripts
#
# Developed for the LSST Data Management System.
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

__all__ = ["SetSummaryState"]

import asyncio
import importlib
import re

from lsst.ts.scriptqueue.base_script import BaseScript
from lsst.ts import salobj


class SetSummaryState(BaseScript):
    """Set the summary state for one or more CSCs.

    Notes
    -----
    **Checkpoints**

    * "set {csc_name}:{index}" before commanding a CSC.

    **Details**

    * Takes the shortest path from the current state to the requested state.
      Thus if you want to configure a CSC you should specify it twice:

      * First with state "STANDBY".
      * Next with state "DISABLED" or "ENABLED" and the desired settings.

    * Dynamically loads SALPY libraries as needed.
    """

    def __init__(self, index):
        super().__init__(index=index, descr="Put CSCs into specified states")

        self.valid_transitions = ['start', 'enable', 'disable', 'standby']

        # approximate time to construct a Remote for a CSC (sec)
        self.create_remote_time = 15
        # time limit for each state transition command (sec);
        # make it generous enough to handle any CSC
        self.cmd_timeout = 10

    async def configure(self, data):
        """Configure the script.

        Specify the CSCs to command, and for each CSC,
        specify the desired summary state optionally the settings.

        Parameters
        ----------
        data : `List` [ `any` ]
            A list of CSC name:index, state and optional settings.
            Each element is a tuple with two or three entries:

                * CSC name and optional index as ``csc_name:index`` (a `str`).
                  For a CSC that is not indexed you may omit ``:index``
                  or specify ``:0``, as you prefer.
                * Name of desired summary state, case blind, e.g. "enabled"
                  or "STANDBY". The "fault" state is not supported.
                * The value of ``settingsToApply`` in the ``start`` command
                  for each CSC. Ignored unless the ``start`` command is issued
                  (i.e. the CSC transitions from "STANDBY" to "DISABLED").
                  If omitted then "" is used.

        Raises
        ------
        ValueError
            If ``data`` has no elements or if any element is not a sequence
            of 2 or 3 elements.
            If the SALPY library cannot be imported for any specified CSC.
            If the desired summary state name is unknown or is "fault".

        Notes
        -----
        Saves the results as two attributes:

        * ``nameind_state_settings``: a list, each element of which is a tuple:

            * (csc_name, index)
            * desired summary state, as an `lsst.ts.salobj.State`
            * settings string, or "" if none specified

        * remotes: a dict of (csc_name, index): remote,
          an `lsst.ts.salobj.Remote`

        Constructing a `salobj.Remote` is slow (DM-17904), so configuration
        may take a 10s or 100s of seconds per CSC.
        """
        self.log.info("Configure started")

        # parse the data
        if len(data) == 0:
            raise ValueError(f"data is an empty list")
        nameind_state_settings = []
        for elt in data:
            if len(data) not in (2, 3):
                raise ValueError(f"{elt} must have 2 or 3 elements")
            match = re.match(r"(?P<name>[a-zA-Z_-]+)(:(?P<index>\d+))?$", elt[0])
            if not match:
                raise ValueError(f"{elt}[0] is not of the form CSC_name:index")
            name = match["name"]
            index = 0 if match["index"] is None else int(match["index"])
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
                settings = elt[2]
                if not isinstance(settings, str):
                    raise ValueError(f"{elt} settings {settings!r} is not a string")
            else:
                settings = ""
            nameind_state_settings.append(((name, index), state, settings))

        # construct remotes
        remotes = dict()
        for elt in nameind_state_settings:
            name_index = elt[0]
            self.log.debug(f"Create remote {name_index[0]}:{name_index[1]}")
            if name_index not in remotes:
                remotes[name_index] = await self.create_remote(name_index)

        self.nameind_state_settings = nameind_state_settings
        self.remotes = remotes

    async def create_remote(self, name_index):
        """Create and return a salobj.Remote for one CSC.

        Parameters
        ----------
        name_index : `List` [ `str`, `int` ]
            CSC name and SAL index.

        Returns
        -------
        remote : `salobj.Remote`
            Remote to talk to the specified CSC. It can send any command
            but only listens to one event: ``summaryState``.

        Notes
        -----
        Warning: this is slow, due to DM-17904.
        """
        name, index = name_index
        sallib = importlib.import_module(f"SALPY_{name}")

        # construct the Remote in a thread to avoid blocking
        def thread_func(name, index):
            return salobj.Remote(sallib, index, include=["summaryState"])

        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, thread_func, name, index)

    def set_metadata(self, metadata):
        """Compute estimated duration.

        Parameters
        ----------
        metadata : SAPY_Script.Script_logevent_metadataC
        """
        # a crude estimate; state transitions are typically quick
        # but we don't know how many of them there will be
        metadata.duration = len(self.nameind_state_settings)*2

    async def run(self):
        """Run script."""
        for name_index, state, settings in self.nameind_state_settings:
            name, index = name_index
            await self.checkpoint(f"set {name}:{index}")
            remote = self.remotes[(name, index)]
            await salobj.set_summary_state(remote, state, settings, timeout=self.cmd_timeout)