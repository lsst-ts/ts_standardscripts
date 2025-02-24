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

__all__ = ["Measure"]

import asyncio

import yaml
from lsst.ts.idl.enums.LaserTracker import LaserStatus
from lsst.ts.observatory.control import RemoteGroup
from lsst.ts.observatory.control.remote_group import Usages
from lsst.ts.standardscripts.base_block_script import BaseBlockScript

from .align import AlignComponent


class Measure(BaseBlockScript):
    """Measure component using laser tracker.

    Parameters
    ----------
    index : `int`
        Index of Script SAL component.

    Notes
    -----
    **Checkpoints**
    - "Starting measure procedure.": Starting measurement with laser tracker.
    - "M2 Hexapod measured with laser tracker.": M2 measured.
    - "Camera Hexapod measured with laser tracker.": Camera measured.
    """

    def __init__(self, index: int, add_remotes: bool = True):
        super().__init__(index, descr="Measure MTCS components with laser tracker.")

        self.laser_tracker = RemoteGroup(
            domain=self.domain,
            components=["LaserTracker:1"],
            intended_usage=None if add_remotes else Usages.DryTest,
            log=self.log,
        )

        self.timeout_measure = 120
        self.timeout_std = 130
        self.timeout_short = 10

        self.target = None

    @classmethod
    def get_schema(cls):
        url = "https://github.com/lsst-ts/"
        path = (
            "ts_externalscripts/blob/main/python/lsst/ts/standardscripts/"
            "maintel/laser_tracker/measure.py"
        )
        schema_yaml = f"""
        $schema: http://json-schema.org/draft-07/schema#
        $id: {url}{path}
        title: MaintelLaserTrackerAlign v1
        description: Configuration for Maintel laser tracker measurement SAL Script.
        type: object
        properties:
            target:
                description: Target to measure.
                type: string
                enum: {[target.name for target in AlignComponent]}
        additionalProperties: false
        required:
            - target
        """
        schema_dict = yaml.safe_load(schema_yaml)

        base_schema_dict = super().get_schema()

        for properties in base_schema_dict["properties"]:
            schema_dict["properties"][properties] = base_schema_dict["properties"][
                properties
            ]

        return schema_dict

    async def configure(self, config):
        self.target = getattr(AlignComponent, config.target)
        await super().configure(config=config)

    def set_metadata(self, metadata):
        """Set estimated duration of the script."""

        metadata.duration = self.timeout_measure + self.timeout_std

    async def measure_target(self):
        """Measure target with laser tracker."""

        self.laser_tracker.rem.lasertracker_1.evt_offsetsPublish.flush()

        await self.laser_tracker.rem.lasertracker_1.cmd_align.set_start(
            target=self.target,
            timeout=self.timeout_measure,
        )

    async def check_laser_status_ok(self):
        """Check that laser status is ON."""
        try:
            laser_status = (
                await self.laser_tracker.rem.lasertracker_1.evt_laserStatus.aget(
                    timeout=self.timeout_short,
                )
            )

            if laser_status.status != LaserStatus.ON:
                raise RuntimeError(
                    f"Laser status is {LaserStatus(laser_status.status)!r}, expected {LaserStatus.ON!r}."
                )
        except asyncio.TimeoutError:
            self.log.warning("Cannot determine Laser Tracker state, continuing.")

    async def run_block(self):
        """Run the script."""

        await self.check_laser_status_ok()

        await self.checkpoint("Starting measuring procedure.")

        # Align component
        await self.measure_target()
        await self.checkpoint(f"{self.target} measured with laser tracker.")
