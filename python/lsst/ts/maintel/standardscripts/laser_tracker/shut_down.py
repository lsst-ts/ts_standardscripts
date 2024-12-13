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

__all__ = ["ShutDown"]

from lsst.ts.idl.enums.LaserTracker import LaserStatus
from lsst.ts.observatory.control import RemoteGroup
from lsst.ts.observatory.control.remote_group import Usages
from lsst.ts.standardscripts.base_block_script import BaseBlockScript


class ShutDown(BaseBlockScript):
    """Shut down Laser Tracker.

    Parameters
    ----------
    index : `int`
        Index of Script SAL component.

    Notes
    -----
    **Checkpoints**
    - "Shutting down Laser Tracker.": Turning laser power off.
    - "Waiting for laser to switch off.": Waiting laser to switch off.
    """

    def __init__(self, index, add_remotes: bool = True):
        super().__init__(index, descr="Shut down laser tracker.")

        self.config = None

        self.laser_tracker = RemoteGroup(
            domain=self.domain,
            components=["LaserTracker:1"],
            intended_usage=None if add_remotes else Usages.DryTest,
            log=self.log,
        )

        self.timeout_laser_warmdown = 60
        self.timeout_laser_power = 30
        self.timeout_std = 60

    @classmethod
    def get_schema(cls):
        return None

    async def configure(self, config):
        self.config = config

    def set_metadata(self, metadata):
        """Set estimated duration of the script."""

        metadata.duration = self.timeout_laser_power + self.timeout_laser_warmdown

    async def wait_laser_status_off(self):
        """Wait for the laser to turn power off."""

        self.log.info("Checking if the laser is turned off.")

        self.laser_tracker.rem.lasertracker_1.evt_laserStatus.flush()
        laser_status = await self.laser_tracker.rem.lasertracker_1.evt_laserStatus.aget(
            timeout=self.timeout_std,
        )

        while laser_status.status != LaserStatus.OFF:
            laser_status = (
                await self.laser_tracker.rem.lasertracker_1.evt_laserStatus.next(
                    flush=False,
                    timeout=self.timeout_laser_warmdown,
                )
            )

    async def run_block(self):
        """Run the script."""

        await self.checkpoint("Shutting down Laser Tracker.")
        await self.laser_tracker.rem.lasertracker_1.cmd_laserPower.set_start(
            power=0,
            timeout=self.timeout_laser_power,
        )

        await self.checkpoint("Waiting for laser to switch off.")
        await self.wait_laser_status_off()

        self.log.info("Laser Tracker is off.")
