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

__all__ = ["EnableM1M3BalanceSystem"]

import time

from lsst.ts.observatory.control.maintel.mtcs import MTCS
from lsst.ts.standardscripts.base_block_script import BaseBlockScript


class EnableM1M3BalanceSystem(BaseBlockScript):
    """Enable M1M3 force balance system.

    Parameters
    ----------
    index : `int`
        Index of Script SAL component.

    Notes
    -----
    **Checkpoints**

    - "Enabling M1M3 force balance system": Before enabling M1M3 force balance
    system.

    **Details**

    This script enables the M1M3 force balance system of the Simonyi Main
    Telescope.


    """

    def __init__(self, index):
        super().__init__(index=index, descr="Enable M1M3 force balance system")

        self.mtcs = None

    async def configure(self, config):
        if self.mtcs is None:
            self.mtcs = MTCS(self.domain, log=self.log)
            await self.mtcs.start_task
        await super().configure(config=config)

    def set_metadata(self, metadata):
        metadata.duration = 180.0

    async def run_block(self):
        await self.checkpoint("Enabling M1M3 force balance system")
        start_time = time.time()
        await self.mtcs.enable_m1m3_balance_system()
        end_time = time.time()
        elapsed_time = end_time - start_time
        self.log.info(
            f"Enabling M1M3 force balance system took {elapsed_time:.2f} seconds"
        )
