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

__all__ = ["OffsetATCS"]

from lsst.ts.observatory.control.auxtel import ATCS, ATCSUsages
from lsst.ts.standardscripts.base_offset_tcs import BaseOffsetTCS


class OffsetATCS(BaseOffsetTCS):
    """Perform an ATCS offset.

    Parameters
    ----------
    index : `int`
        Index of Script SAL component.
    """

    def __init__(self, index, add_remotes: bool = True):
        super().__init__(
            index=index,
            descr="Perform an ATCS offset",
        )

        atcs_usage = None if add_remotes else ATCSUsages.DryTest

        self.atcs = ATCS(domain=self.domain, intended_usage=atcs_usage, log=self.log)

    @property
    def tcs(self):
        return self.atcs
