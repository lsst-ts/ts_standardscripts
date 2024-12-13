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

__all__ = ["SetUp"]

import asyncio

from lsst.ts.idl.enums.LaserTracker import LaserStatus
from lsst.ts.observatory.control import RemoteGroup
from lsst.ts.observatory.control.remote_group import Usages
from lsst.ts.standardscripts.base_block_script import BaseBlockScript


class SetUp(BaseBlockScript):
    """Set up Laser Tracker.

    Parameters
    ----------
    index : `int`
        Index of Script SAL component.

    Notes
    -----
    **Checkpoints**
    - "Power up Laser Tracker.": Turning laser power on.
    - "Waiting for laser to warm up.": Waiting for laser to warm up.

    """

    def __init__(self, index: int, add_remotes: bool = True):
        super().__init__(index, descr="Set up laser tracker.")

        self.config = None

        self.laser_tracker = RemoteGroup(
            domain=self.domain,
            components=["LaserTracker:1"],
            intended_usage=None if add_remotes else Usages.DryTest,
            log=self.log,
        )
        self.timeout_laser_warmup = 60
        self.timeout_laser_power = 30
        self.timeout_std = 60

    @classmethod
    def get_schema(cls):
        return None

    async def configure(self, config):
        self.config = config

    def set_metadata(self, metadata):
        """Set estimated duration of the script."""

        metadata.duration = self.timeout_laser_warmup + self.timeout_laser_power

    async def start_up(self):
        """Start up the Laser Tracker and check it is alived and enabled."""

        if self.laser_tracker.start_task is not None:
            await self.laser_tracker.start_task

        await asyncio.gather(
            self.laser_tracker.assert_liveliness(),
            self.laser_tracker.assert_all_enabled(),
        )

    async def wait_laser_status_ok(self):
        """Wait for the laser to warm up and be ready to be used."""

        self.log.info("Checking if the laser is ready to be used.")

        self.laser_tracker.rem.lasertracker_1.evt_laserStatus.flush()
        laser_status = await self.laser_tracker.rem.lasertracker_1.evt_laserStatus.aget(
            timeout=self.timeout_std,
        )

        while laser_status.status != LaserStatus.ON:
            laser_status = (
                await self.laser_tracker.rem.lasertracker_1.evt_laserStatus.next(
                    flush=False,
                    timeout=self.timeout_laser_warmup,
                )
            )

    async def run_block(self):
        """Run the script."""
        await self.start_up()

        await self.checkpoint("Power up Laser Tracker.")
        await self.laser_tracker.rem.lasertracker_1.cmd_laserPower.set_start(
            power=1,
            timeout=self.timeout_laser_power,
        )

        await self.checkpoint("Waiting for laser to warm up.")
        await self.wait_laser_status_ok()

        self.log.info("Laser Tracker is warmed up and ready to be used.")
