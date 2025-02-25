# This file is part of ts_auxtel_standardscripts
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

__all__ = ["Stop"]

from lsst.ts import salobj
from lsst.ts.observatory.control.auxtel.atcs import ATCS, ATCSUsages


class Stop(salobj.BaseScript):
    """Stop telescope and dome.

    Parameters
    ----------
    index : `int`
        Index of Script SAL component.

    Notes
    -----
    **Checkpoints**

    TBD

    **Details**

    TBD

    """

    def __init__(self, index):
        super().__init__(index=index, descr="Enable ATCS.")

        self.config = None

        self.attcs = ATCS(self.domain, intended_usage=ATCSUsages.Shutdown, log=self.log)

    @classmethod
    def get_schema(cls):
        return None

    async def configure(self, config):
        self.config = config

    def set_metadata(self, metadata):
        metadata.duration = 60.0

    async def run(self):
        await self.attcs.stop_all()
