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

__all__ = ["LowerM1M3"]

import time

from lsst.ts.observatory.control.maintel.mtcs import MTCS
from lsst.ts.standardscripts.base_block_script import BaseBlockScript


class LowerM1M3(BaseBlockScript):
    """Lower M1M3 mirror.

    Parameters
    ----------
    index : `int`
        Index of Script SAL component.

    Notes
    -----
    **Checkpoints**

    - "Lowering M1M3": Before commanding the M1M3 mirror to lower.

    **Details**

    This script lowers the M1M3 mirror of the Simonyi Main Telescope.


    """

    def __init__(self, index):
        super().__init__(index=index, descr="Lower M1M3")

        self.mtcs = None

    async def configure(self, config):
        if self.mtcs is None:
            self.mtcs = MTCS(self.domain, log=self.log)
            await self.mtcs.start_task
        await super().configure(config=config)

    def set_metadata(self, metadata):
        metadata.duration = 180.0

    async def run_block(self):
        await self.checkpoint("Lowering M1M3")
        start_time = time.time()
        await self.mtcs.lower_m1m3()
        end_time = time.time()
        elapsed_time = end_time - start_time
        self.log.info(f"Lowering M1M3 took {elapsed_time:.2f} seconds")
