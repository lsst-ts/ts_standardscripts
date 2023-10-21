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

__all__ = ["Sleep"]

import asyncio

import yaml
from lsst.ts.salobj import BaseScript


class Sleep(BaseScript):
    """Sleep for a given amount of time.

    This script pauses the script queue for a specified amount of time.

    Parameters
    ----------
    index : `int`
        Index of Script SAL component.

    Notes
    -----
    **Details**

    This script sends a sleep command to the script queue, which pauses
    the script queue for a specified amount of time.

    """

    def __init__(self, index):
        super().__init__(index=index, descr="Pause the script queue.")

        self.sleep_for = 0

    @classmethod
    def get_schema(cls):
        schema_yaml = """
            $schema: http://json-schema.org/draft-07/schema#
            $id: https://github.com/lsst-ts/ts_standardscripts/sleep.yaml
            title: Sleep v1
            description: Configuration for Sleep command.
            type: object
            properties:
                sleep_for:
                    description: >-
                        Duration of the sleep command in seconds.
                    type: number
                    minimum: 0
            additionalProperties: false
        """
        return yaml.safe_load(schema_yaml)

    async def configure(self, config):
        """Configure the script.

        Parameters
        ----------
        config : `types.SimpleNamespace`
            Configuration
        """
        self.sleep_for = config.sleep_for

    def set_metadata(self, metadata):
        metadata.duration = self.sleep_for

    async def run(self):
        self.log.info(f"Sleep queue for {self.sleep_for} seconds...")
        await asyncio.sleep(self.sleep_for)
