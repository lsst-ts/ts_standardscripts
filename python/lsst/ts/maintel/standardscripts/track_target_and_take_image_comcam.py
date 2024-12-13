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

__all__ = ["TrackTargetAndTakeImageComCam"]

import asyncio

from lsst.ts.observatory.control.maintel.comcam import ComCam, ComCamUsages
from lsst.ts.observatory.control.maintel.mtcs import MTCS, MTCSUsages
from lsst.ts.observatory.control.utils import RotType
from lsst.ts.standardscripts.base_track_target_and_take_image import (
    BaseTrackTargetAndTakeImage,
)


class TrackTargetAndTakeImageComCam(BaseTrackTargetAndTakeImage):
    """Track target and take image script.

    This script implements a simple visit consistig of slewing to a target,
    start tracking and take image.

    Parameters
    ----------
    index : `int`
        Index of Script SAL component.
    add_remotes : `bool` (optional)
        Create remotes to control components (default: `True`)? If False, the
        script will not work for normal operations. Useful for unit testing.
    """

    def __init__(self, index, add_remotes: bool = True):
        super().__init__(
            index=index, descr="Track target and take image with MainTel and ComCam."
        )

        mtcs_usage, comcam_usage = (
            (
                MTCSUsages.Slew | MTCSUsages.StateTransition,
                ComCamUsages.TakeImageFull | ComCamUsages.StateTransition,
            )
            if add_remotes
            else (MTCSUsages.DryTest, ComCamUsages.DryTest)
        )

        self.angle_filter_change = 0.0
        self.tolerance_angle_filter_change = 1e-2

        self.mtcs = MTCS(self.domain, intended_usage=mtcs_usage, log=self.log)
        self.comcam = ComCam(self.domain, intended_usage=comcam_usage, log=self.log)

        self.instrument_name = "LSSTComCam"

    @property
    def tcs(self):
        return self.mtcs

    @classmethod
    def get_schema(cls):
        schema_dict = cls.get_base_schema()
        schema_dict["$id"] = (
            "https://github.com/lsst-ts/ts_standardscripts/maintel/track_target_and_take_image_comcam.py"
        )
        schema_dict["title"] = "TrackTargetAndTakeImageComCam v1"
        schema_dict["description"] = "Configuration for TrackTargetAndTakeImageComCam."

        return schema_dict

    def get_instrument_name(self):
        return self.instrument_name

    async def load_playlist(self):
        """Load playlist."""
        await self.comcam.rem.cccamera.cmd_play.set_start(
            playlist=self.config.camera_playlist,
            repeat=True,
            timeout=self.comcam.fast_timeout,
        )

    async def assert_feasibility(self):
        """Verify that the system is in a feasible state to execute the
        script.
        """
        await asyncio.gather(
            self.mtcs.assert_all_enabled(),
            self.comcam.assert_all_enabled(),
        )

    async def track_target_and_setup_instrument(self):
        """Track target and setup instrument in parallel."""

        current_filter = await self.comcam.get_current_filter()

        self.tracking_started = True

        if current_filter != self.config.band_filter:
            self.log.debug(
                f"Filter change required: {current_filter} -> {self.config.band_filter}"
            )
            await self._handle_slew_and_change_filter()
        else:
            self.log.debug(
                f"Already in the desired filter ({current_filter}), slewing and tracking."
            )

        await self.mtcs.slew_icrs(
            ra=self.config.ra,
            dec=self.config.dec,
            rot=self.config.rot_sky,
            rot_type=RotType.Sky,
            target_name=self.config.name,
            az_wrap_strategy=self.config.az_wrap_strategy,
            time_on_target=self.get_estimated_time_on_target(),
        )

    async def _handle_slew_and_change_filter(self):
        """Handle slewing and changing filter at the same time.

        For ComCam (and MainCam) we need to send the rotator to zero and keep
        it there while the filter is changing.
        """

        await self.mtcs.slew_icrs(
            ra=self.config.ra,
            dec=self.config.dec,
            rot=self.angle_filter_change,
            rot_type=RotType.Physical,
            target_name=f"{self.config.name} - filter change",
            az_wrap_strategy=self.config.az_wrap_strategy,
            time_on_target=self.get_estimated_time_on_target(),
        )

        await self.comcam.setup_filter(filter=self.config.band_filter)

    async def _wait_rotator_reach_filter_change_angle(self):
        """Wait until the rotator reach the filter change angle."""

        while True:
            rotator_position = await self.mtcs.rem.mtrotator.tel_rotation.next(
                flush=True, timeout=self.mtcs.fast_timeout
            )

            if (
                abs(rotator_position.actualPosition - self.angle_filter_change)
                < self.tolerance_angle_filter_change
            ):
                self.log.debug("Rotator inside tolerance range.")
                break
            else:
                self.log.debug(
                    "Rotator not in position: "
                    f"{rotator_position.actualPosition} -> {self.angle_filter_change}"
                )
                await asyncio.sleep(self.mtcs.tel_settle_time)

    async def take_data(self):
        """Take data while making sure ATCS is tracking."""

        tasks = [
            asyncio.create_task(self._take_data()),
            asyncio.create_task(self.mtcs.check_tracking()),
        ]

        await self.mtcs.process_as_completed(tasks)

    async def _take_data(self):
        """Take data."""

        for exptime in self.config.exp_times:
            await self.comcam.take_object(
                exptime=exptime,
                group_id=self.group_id,
                reason=self.config.reason,
                program=self.config.program,
            )

    async def stop_tracking(self):
        """Execute stop tracking on MTCS."""
        await self.mtcs.stop_tracking()
