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

__all__ = ["DisableM2ClosedLoop"]

import time

from lsst.ts.observatory.control.maintel.mtcs import MTCS
from lsst.ts.standardscripts.base_block_script import BaseBlockScript


class DisableM2ClosedLoop(BaseBlockScript):
    """Disable M2 closed-loop.

    Parameters
    ----------
    index : `int`
        Index of Script SAL component.

    Notes
    -----
    **Checkpoints**

    - "Disabling M1M2 closed-loop": Before disabling M2 closed-loop.

    **Details**

    This script disables M2 closed-loop for the Simonyi Survey Telescope.
    """

    def __init__(self, index):
        super().__init__(index=index, descr="Disable M2 closed-loop.")
        self.mtcs = None

    async def configure_tcs(self) -> None:
        if self.mtcs is None:
            self.log.debug("Creating MTCS.")
            self.mtcs = MTCS(domain=self.domain, log=self.log)
            await self.mtcs.start_task
        else:
            self.log.debug("MTCS already defined, skipping.")

    async def configure(self, config):
        await self.configure_tcs()
        await super().configure(config=config)

    def set_metadata(self, metadata):
        metadata.duration = 15.0

    async def run_block(self):
        await self.checkpoint("Disabling M2 closed-loop.")
        start_time = time.monotonic()
        await self.mtcs.disable_m2_balance_system()
        elapsed_time = time.monotonic() - start_time
        self.log.info(f"Disabling M2 closed-loop took {elapsed_time:.2f} seconds.")
