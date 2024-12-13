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

__all__ = ["TrackTarget"]

from lsst.ts.observatory.control.maintel.mtcs import MTCS, MTCSUsages
from lsst.ts.standardscripts.base_track_target import BaseTrackTarget


class TrackTarget(BaseTrackTarget):
    """Execute a Slew/Track operation with the Main Telescope.

    Parameters
    ----------
    index : `int`
        Index of Script SAL component.

    Notes
    -----
    **Checkpoints**

    None

    """

    def __init__(self, index):
        super().__init__(
            index=index, descr="Slew and track a target with the main telescope."
        )
        self._mtcs = None

    @property
    def tcs(self):
        return self._mtcs

    async def configure_tcs(self):
        if self._mtcs is None:
            self._mtcs = MTCS(self.domain, intended_usage=MTCSUsages.Slew, log=self.log)
        await super().configure_tcs()
