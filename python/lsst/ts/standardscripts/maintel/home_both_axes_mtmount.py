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

__all__ = ["HomeBothAxesMTMount"]

import time

from lsst.ts.observatory.control.maintel.mtcs import MTCS, MTCSUsages

from lsst.ts import salobj


class HomeBothAxesMTMount(salobj.BaseScript):
    """Home azimuth and elevation axes in MTMount.Must call this after powering
    on the main axis and BEFORE you can move them.

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

    def __init__(self, index, add_remotes: bool = True):
        super().__init__(index=index, descr="Raise M1M3")

        mtcs_usage = None if add_remotes else MTCSUsages.DryTest

        self.mtcs = MTCS(self.domain, intended_usage=mtcs_usage, log=self.log)

    @classmethod
    def get_schema(cls):
        return None

    async def configure(self, config):
        # This script does not require any configuration.
        self.config = config

    def set_metadata(self, metadata):
        metadata.duration = 60 * 3

    async def run(self):
        # await self.checkpoint("Homing Both Axes")
        start_time = time.time()
        await self.mtcs.rem.mtmount.cmd_homeBothAxes.set_start()
        end_time = time.time()
        elapsed_time = end_time - start_time
        
        self.log.info(f"Homing both axes took {elapsed_time:.2f} seconds")
