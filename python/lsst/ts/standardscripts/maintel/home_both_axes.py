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
# along with this program.  If not, see <https://www.gnu.org/licenses/>.``

__all__ = ["HomeBothAxes"]

import time

from lsst.ts import salobj
from lsst.ts.observatory.control.maintel.mtcs import MTCS


class HomeBothAxes(salobj.BaseScript):
    """Home azimuth and elevation axes of the MTMount.
    Must call this after powering on the main axis and
    BEFORE you move them.

    Parameters
    ----------
    index : `int`
        Index of Script SAL component.

    Notes
    -----
    **Checkpoints**

    - "Homing Both Axes": Before commanding both axes to be homed.

    **Details**

    This script homes both aximuth and elevation axes of
    the Simonyi Main Telescope mount.


    """

    def __init__(self, index):
        super().__init__(index=index, descr="Raise M1M3")

        self.home_both_axes_timeout = 300.0  # timeout to home both MTMount axes.

    @classmethod
    def get_schema(cls):
        return None

    async def configure(self, config):
        # This script does not require any configuration.
        if self.mtcs is None:
            self.mtcs = MTCS(domain=self.domain, log=self.log)

    def set_metadata(self, metadata):
        metadata.duration = self.home_both_axes_timeout

    async def run(self):
        await self.checkpoint("Disable M1M3 balance system.")
        await self.mtcs.disable_m1m3_balance_system()

        await self.checkpoint("Homing Both Axes")
        start_time = time.time()
        await self.mtcs.rem.mtmount.cmd_homeBothAxes.start(
            timeout=self.home_both_axes_timeout
        )
        end_time = time.time()
        elapsed_time = end_time - start_time

        self.log.info(f"Homing both axes took {elapsed_time:.2f} seconds")
