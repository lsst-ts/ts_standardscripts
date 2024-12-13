# This file is part of ts_externalcripts
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

__all__ = ["CloseLoopComCam"]

from lsst.ts.observatory.control.maintel.comcam import ComCam
from lsst.ts.observatory.control.utils.enums import ClosedLoopMode

from .base_close_loop import BaseCloseLoop

STD_TIMEOUT = 10


class CloseLoopComCam(BaseCloseLoop):
    """Run Closed Loop with ComCam.

    Parameters
    ----------
    index : `int`, optional
        Index of Script SAL component (default=1).
    remotes : `bool`, optional
        Should the remotes be created (default=True)? For unit testing this
        can be set to False, which allows one to mock the remotes behaviour.
    descr : `str`, optional
        Short description of the script.
    """

    def __init__(self, index, descr="") -> None:
        super().__init__(index=index, descr=descr)

        self.config = None

        self._camera = None

    @property
    def oods(self):
        return self._camera.rem.ccoods

    async def configure_camera(self) -> None:
        """Handle creating Camera object and waiting for remote to start."""
        if self._camera is None:
            self.log.debug("Creating Camera.")

            self._camera = ComCam(
                self.domain,
                log=self.log,
                tcs_ready_to_take_data=self.mtcs.ready_to_take_data,
            )
            await self._camera.start_task
        else:
            self.log.debug("Camera already defined, skipping.")

    async def assert_mode_compatibility(self) -> None:
        """Assert that the mode is compatible with ComCam.

        Raises
        ------
        RuntimeError
            If the mode is not compatible with ComCam.
        """

        if self.mode == ClosedLoopMode.CWFS:
            raise RuntimeError("ComCam does not support CWFS mode.")
