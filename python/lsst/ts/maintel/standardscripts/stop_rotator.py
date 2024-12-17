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

__all__ = ["StopRotator"]

from lsst.ts import salobj
from lsst.ts.observatory.control.maintel.mtcs import MTCS


class StopRotator(salobj.BaseScript):
    """A script that executes stop_rotator method for `MTCS`

    Parameters
    ----------
    index : `int`
        Index of Script SAL component.

    Notes
    -----
    **Checkpoints**

    Stopping rotator: Before issuing stop command.
    Done: After issuing stop command.
    """

    def __init__(self, index):
        super().__init__(index=index, descr="MTCS stop rotator.")
        self.mtcs = None

    @classmethod
    def get_schema(cls):
        return None

    async def configure(self, config):
        if self.mtcs is None:
            self.mtcs = MTCS(domain=self.domain, log=self.log)

    def set_metadata(self, metadata):
        metadata.duration = self.mtcs.tel_settle_time

    async def run(self):
        await self.checkpoint("Stopping rotator...")
        await self.mtcs.stop_rotator()
        await self.checkpoint("Done")
