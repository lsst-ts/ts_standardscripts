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

__all__ = ["TakeAOSSequenceBalancedComCam"]


from lsst.ts.standardscripts.maintel import TakeAOSSequenceComCam


class TakeAOSSequenceBalancedComCam(TakeAOSSequenceComCam):
    """Take aos sequence, either triplet (intra-focal, extra-focal
    and in-focus images), intra doublets (intra and in-focus) or extra
    doublets (extra and in-focus) sequences with ComCam.

    This version splits the dz offset evenly between the camera and M2
    hexapods.

    Parameters
    ----------
    index : `int`
        Index of Script SAL component.

    Notes
    -----
    **Checkpoints**

    * sequence {n} of {m}: before taking a sequence.

    """

    async def _apply_z_offset(self, z_offset: float) -> None:
        """Apply dz offset.

        Parameters
        ----------
        z_offset : float
            dz offset to apply, in microns.
        """
        await self.mtcs.offset_camera_hexapod(x=0, y=0, z=z_offset / 2, u=0, v=0)
        await self.mtcs.offset_m2_hexapod(x=0, y=0, z=z_offset / 2, u=0, v=0)
