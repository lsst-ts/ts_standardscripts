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

__all__ = ["RaiseM1M3"]

import time

from lsst.ts.observatory.control.maintel.mtcs import MTCS, MTCSUsages

from ...base_block_script import BaseBlockScript


class RaiseM1M3(BaseBlockScript):
    """Raise M1M3 mirror.

    Parameters
    ----------
    index : `int`
        Index of Script SAL component.

    Notes
    -----
    **Checkpoints**

    - "Raising M1M3": Before commanding the M1M3 mirror to raise.

    **Details**

    This script raises the M1M3 mirror of the Simonyi Main Telescope.


    """

    def __init__(self, index, add_remotes: bool = True):
        super().__init__(index=index, descr="Raise M1M3")

        mtcs_usage = None if add_remotes else MTCSUsages.DryTest

        self.mtcs = MTCS(self.domain, intended_usage=mtcs_usage, log=self.log)

    def set_metadata(self, metadata):
        metadata.duration = 180.0

    async def run_block(self):
        await self.checkpoint("Raising M1M3")
        start_time = time.time()
        await self.mtcs.raise_m1m3()
        end_time = time.time()
        elapsed_time = end_time - start_time
        self.log.info(f"M1M3 Raise took {elapsed_time:.2f} seconds")
