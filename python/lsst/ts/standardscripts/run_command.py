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

__all__ = ["RunCommand"]

import yaml
from lsst.ts import salobj


class RunCommand(salobj.BaseScript):
    """Run a command from a CSC and, optionally, wait for an event once the
    command finishes.

    Notes
    -----
    **Checkpoints**

    * "run {csc_name}:{index}:{cmd}" before commanding a CSC.

    * "wait {csc_name}:{index}:{event}" after commanding a CSC and before
      waiting for the event.

    **Details**

    * Dynamically loads IDL files as needed.
    """

    def __init__(self, index):
        super().__init__(index=index, descr="Run command from CSC.")

        # approximate time to construct a Remote for a CSC (sec)
        self.create_remote_time = 15

    @classmethod
    def get_schema(cls):
        schema_yaml = """
            $schema: http://json-schema.org/draft-07/schema#
            $id: https://github.com/lsst-ts/ts_standardscripts/RunCommand.yaml
            title: RunCommand v1
            description: Configuration for RunCommand.
            type: object
            properties:
              component:
                description: Name of the CSC to run command, format is
                    CSC_name[:index]; the default index is 0.
                type: string
              cmd:
                description: Name of the command to run.
                type: string
              event:
                description: >-
                    Name of the event to wait after the command is sent.
                type: string
              flush:
                description: Flush event before sending command?
                type: boolean
                default: True
              event_timeout:
                description: Timeout (seconds) to wait for the event to arrive.
                type: number
                default: 30
              parameters:
                description: Parameters for the command.
                type: object
                properties:
                  timeout:
                    description: Timeout (seconds) to wait for the command to complete.
                    type: number
                    default: 30
                additionalProperties: true
            required: [component, cmd]
            additionalProperties: false
        """
        return yaml.safe_load(schema_yaml)

    async def configure(self, config):
        """Configure the script.

        Specify the CSCs to command, the command to run, the parameters for
        the command. Optionally, specify an event to wait and if the event
        should be flushed before sending the command.

        Parameters
        ----------
        config : `types.SimpleNamespace`

        Raises
        ------
        RuntimeError:
            If `config.command` is not a valid command from the CSC.

        """
        self.log.info("Configure started")

        self.config = config

        self.name, self.index = salobj.name_to_name_index(config.component)
        self.event = config.event if hasattr(config, "event") else None

        self.remote = salobj.Remote(
            domain=self.domain,
            name=self.name,
            index=self.index,
            include=[self.event] if self.event is not None else [],
        )

        if config.cmd in self.remote.salinfo.command_names:
            self.cmd = config.cmd
        else:
            raise RuntimeError(
                f"Command {config.cmd} not a valid command for {self.name}."
            )

        getattr(self.remote, f"cmd_{self.cmd}").set(
            **dict(
                [(k, config.parameters[k]) for k in config.parameters if k != "timeout"]
            )
        )

        self.flush = config.flush if self.event is not None else False

        if self.event is not None and self.event not in self.remote.salinfo.event_names:
            raise RuntimeError(f"Event {self.event} not a valid event for {self.name}.")

    def set_metadata(self, metadata):
        """Compute estimated duration.

        Parameters
        ----------
        metadata : `Script_logevent_metadata`

        """
        # a crude estimate using command and event timeouts.
        metadata.duration = (
            self.config.parameters["timeout"] + self.config.event_timeout
            if self.flush
            else 0.0
        )

    async def run(self):
        """Run script."""

        if not self.remote.start_task.done():
            self.log.debug("Waiting for remote start_task to complete.")
            await self.remote.start_task

        if self.flush:
            getattr(self.remote, f"evt_{self.event}").flush()

        await self.checkpoint(f"run {self.name}:{self.index}:{self.cmd}")

        await getattr(self.remote, f"cmd_{self.cmd}").start(
            timeout=self.config.parameters["timeout"]
        )

        if self.event is not None:
            await self.checkpoint(f"wait {self.name}:{self.index}:{self.event}")

            evt = await getattr(self.remote, f"evt_{self.event}").next(
                flush=False, timeout=self.config.event_timeout
            )

            self.log.info(evt)
