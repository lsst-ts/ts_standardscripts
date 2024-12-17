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
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

__all__ = ["PointAzEl"]

from lsst.ts.observatory.control.auxtel.atcs import ATCS
from lsst.ts.standardscripts.base_point_azel import BasePointAzEl


class PointAzEl(BasePointAzEl):
    """Auxiliary Telescope point_azel script.

    Parameters
    ----------
    index : `int`
        Index of Script SAL component.

    """

    def __init__(self, index):
        super().__init__(
            index=index,
            descr="Slew the auxiliary telescope to a pair of (az, el) coordinates.",
        )

        self.atcs = None
        self.slew_time_guess = 180

    @property
    def tcs(self):
        return self.atcs

    async def configure_tcs(self):
        """Handle creating ATCS object and waiting for remote to start."""

        if self.atcs is None:
            self.log.debug("Creating ATCS")
            self.atcs = ATCS(self.domain, log=self.log)
            await self.atcs.start_task

    def set_metadata(self, metadata):
        metadata.duration = self.slew_time_guess
