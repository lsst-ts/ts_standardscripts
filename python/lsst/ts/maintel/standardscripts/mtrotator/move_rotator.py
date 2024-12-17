# This file is part of ts_maintel_standardscripts
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

__all__ = ["MoveRotator"]

import yaml
from lsst.ts.observatory.control.maintel.mtcs import MTCS
from lsst.ts.standardscripts.base_block_script import BaseBlockScript


class MoveRotator(BaseBlockScript):
    """Move the rotator to a given angle. It has the option of completing the
    script before the rotator reaches the desired angle.

    Parameters
    ----------
    index : `int`
        Index of Script SAL component.

    Notes
    -----
    **Checkpoints**

    - "Start moving rotator to {angle} degrees.": Start moving rotator.
    - "Stop script and keep rotator moving.": Stop script.
    - "Rotator reached {angle} degrees.": Rotator reached angle.

    """

    def __init__(self, index: int) -> None:
        super().__init__(index=index, descr="Move Rotator")

        self.mtcs = None

        self.rotator_velocity = 3.5  # degrees per second
        self.short_timeout = 10  # seconds
        self.long_timeout = 120  # seconds

    @classmethod
    def get_schema(cls):
        url = "https://github.com/lsst-ts/"
        path = (
            "ts_standardscripts/blob/main/python/lsst/ts/standardscripts/"
            "maintel/mtrotator/move_rotator.py"
        )
        schema_yaml = f"""
        $schema: http://json-schema.org/draft-07/schema#
        $id: {url}{path}
        title: MoveRotator v1
        description: Configuration for Maintel move rotator SAL Script.
        type: object
        properties:
            angle:
                description: final angle of the rotator.
                type: number
                minimum: -90
                maximum: 90
            wait_for_complete:
                description: >-
                    whether wait for the rotator to reach the desired angle or
                    complete the script before the rotator reaches the desired
                    angle.
                type: boolean
                default: true
        required:
            - angle
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
        """
        Configure the script.

        Parameters
        ----------
        config : `dict`
            Dictionary containing the configuration parameters.
        """
        await self.configure_tcs()

        self.target_angle = config.angle
        self.wait_for_complete = config.wait_for_complete

        await super().configure(config=config)

    async def configure_tcs(self) -> None:
        """
        Handle creating MTCS object and waiting for remote to start.
        """
        if self.mtcs is None:
            self.log.debug("Creating MTCS.")
            self.mtcs = MTCS(
                domain=self.domain,
                log=self.log,
            )
            await self.mtcs.start_task
        else:
            self.log.debug("MTCS already defined, skipping.")

    def set_metadata(self, metadata):
        """Set the metadata for the script."""
        metadata.duration = self.long_timeout

    async def run_block(self):
        """Run the script."""
        await self.checkpoint(f"Start moving rotator to {self.target_angle} degrees.")
        await self.mtcs.move_rotator(
            position=self.target_angle, wait_for_in_position=self.wait_for_complete
        )
        await self.checkpoint(
            f"Move rotator returned. Wait for complete: {self.wait_for_complete}."
        )
