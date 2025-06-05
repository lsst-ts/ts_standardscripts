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

__all__ = ["PauseQueue"]

import types

import yaml
from lsst.ts.observatory.control.script_queue import ScriptQueue
from lsst.ts.salobj import BaseScript
from lsst.ts.xml.enums.ScriptQueue import SalIndex


class PauseQueue(BaseScript):
    """A script to pause the script queue.

    This script will send a command to the script queue to pause it.
    The script will then wait indefinitely until it receives a signal
    to continue.

    Parameters
    ----------
    index : `int`
        Index of Script SAL component.
    """

    def __init__(self, index):
        super().__init__(index=index, descr="Pause the script queue.")

        self.queue_index = None
        self.script_queue = None

    @classmethod
    def get_schema(cls):
        schema_yaml = """
            $schema: http://json-schema.org/draft-07/schema#
            $id: https://github.com/lsst-ts/ts_standardscripts/pause_queue.yaml
            title: PauseQueue v1
            description: Configuration for PauseQueue script.
            type: object
            properties:
                queue:
                    description: >-
                        Which ScriptQueue to pause?
                    type: string
                    enum: ["MAIN_TEL", "AUX_TEL"]
            additionalProperties: false
        """
        return yaml.safe_load(schema_yaml)

    async def configure(self, config: types.SimpleNamespace) -> None:
        """Configure the script.

        Parameters
        ----------
        config : `types.SimpleNamespace`
            Configuration.
        """
        self.queue_index = getattr(SalIndex, config.queue)

        # Initialize the script queue with the selected index
        if self.script_queue is None:
            self.script_queue = ScriptQueue(
                queue_index=self.queue_index, domain=self.domain, log=self.log
            )
            await self.script_queue.start_task

    def set_metadata(self, metadata):
        pass

    async def run(self):
        """Run the script."""

        self.log.info(
            f"Pausing {self.queue_index!r} script queue. Resume the queue when you are ready..."
        )
        await self.script_queue.pause()
