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

__all__ = ["EnableHexapodCompensationMode"]

import asyncio

import yaml
from lsst.ts.observatory.control.maintel.mtcs import MTCS
from lsst.ts.standardscripts.base_block_script import BaseBlockScript


class EnableHexapodCompensationMode(BaseBlockScript):
    """Enable compensation mode for M2 and/or Camera Hexapods.

    Parameters
    ----------
    index : `int`
        Index of Script SAL component.

    Notes
    -----
    **Checkpoints**

    - "Enabling compensation mode": Before enabling compensation mode.

    **Details**

    This script enables the compensation mode for selected hexapods of the
    Simonyi Survey Telescope.

    """

    def __init__(self, index: int) -> None:
        super().__init__(
            index=index,
            descr="Enable Hexapod Compensation Mode.",
        )
        self.mtcs = None

    async def configure_tcs(self) -> None:
        if self.mtcs is None:
            self.log.debug("Creating MTCS.")
            self.mtcs = MTCS(domain=self.domain, log=self.log)
            await self.mtcs.start_task
        else:
            self.log.debug("MTCS already defined, skipping.")

    @staticmethod
    def component_to_hexapod(component):
        hexapod_map = {"M2Hexapod": "mthexapod_2", "CameraHexapod": "mthexapod_1"}
        return hexapod_map.get(component)

    @classmethod
    def get_schema(cls):
        schema_yaml = """
            $schema: http://json-schema.org/draft-07/schema#
            $id: https://github.com/lsst-ts/ts_standardscripts/maintel/enable_hexapod_compensation_mode.yaml
            title: EnableHexapodCompensationMode v1
            description: Configuration for EnableHexapodCompensationMode
            type: object
            properties:
                components:
                    description: List of hexapods to enable compensation mode for.
                    type: array
                    items:
                        type: string
                        enum: ["M2Hexapod", "CameraHexapod"]
                    minItems: 1
                    default: ["M2Hexapod", "CameraHexapod"]
            additionalProperties: false
        """
        schema_dict = yaml.safe_load(schema_yaml)

        base_schema_dict = super().get_schema()

        for properties in base_schema_dict["properties"]:
            schema_dict["properties"][properties] = base_schema_dict["properties"][
                properties
            ]

        return schema_dict

    async def configure(self, config):
        self.config = config
        self.components = config.components
        await self.configure_tcs()

        await super().configure(config=config)

    def set_metadata(self, metadata):
        metadata.duration = 15.0

    async def enable_compensation_for_hexapod(self, hexapod, component):
        await self.checkpoint(f"Enabling compensation mode for {component}")
        await self.mtcs.enable_compensation_mode(hexapod)
        self.log.info(f"Compensation mode enabled for {component}")

    async def run_block(self):
        tasks = []
        for component in self.config.components:
            hexapod = self.component_to_hexapod(component)
            task = asyncio.create_task(
                self.enable_compensation_for_hexapod(hexapod, component)
            )
            tasks.append(task)
        await asyncio.gather(*tasks)
