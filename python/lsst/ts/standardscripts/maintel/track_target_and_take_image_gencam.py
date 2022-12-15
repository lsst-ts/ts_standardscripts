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

__all__ = ["TrackTargetAndTakeImageGenCam"]

import asyncio

from lsst.ts.observatory.control import Usages
from lsst.ts.observatory.control.generic_camera import GenericCamera
from lsst.ts.observatory.control.maintel.mtcs import MTCS, MTCSUsages
from lsst.ts.observatory.control.utils import RotType

from ..base_track_target_and_take_image import BaseTrackTargetAndTakeImage


class TrackTargetAndTakeImageGenCam(BaseTrackTargetAndTakeImage):
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

        # Is there a better way to define this?
        Usages.TakeImageFull = 1 << 4

        self.mtcs_usage, self.gencam_usage = (
            (MTCSUsages.Slew, Usages.TakeImageFull)
            if add_remotes
            else (MTCSUsages.DryTest, Usages.DryTest)
        )

        self.mtcs = MTCS(self.domain, intended_usage=self.mtcs_usage, log=self.log)
        self.gencam = None

    async def load_playlist(self):
        """Load playlist."""
        raise NotImplementedError()

    async def assert_feasibility(self):
        """Verify that the system is in a feasible state to execute the
        script.
        """
        await asyncio.gather(
            self.mtcs.assert_all_enabled(),
            self.mtcs.assert_liveliness(),
            self.gencam.assert_all_enabled(),
            self.gencam.assert_liveliness(),
        )

    async def configure(self, config):
        await super().configure(config)
        self.gencam = GenericCamera(
            self.config.camera_index,
            self.domain,
            intended_usage=self.gencam_usage,
            log=self.log,
        )

    @classmethod
    def get_schema(cls):

        schema_dict = cls.get_base_schema()
        schema_dict[
            "$id"
        ] = "https://github.com/lsst-ts/ts_standardscripts/maintel/track_target_and_take_image_gencam.py"
        schema_dict["title"] = "TrackTargetAndTakeImageGenCam v1"
        schema_dict["description"] = "Configuration for TrackTargetAndTakeImageGenCam."

        schema_dict["camera_index"] = dict(
            type="integer",
            description="SAL Index for the Generic Camera.",
            minimum=0,
            maximum=2147483647,
        )

        schema_dict["required"].append("camera_index")
        schema_dict["required"].remove("band_filter")

        return schema_dict

    async def track_target_and_setup_instrument(self):
        """Track target and setup instrument in parallel."""

        self.tracking_started = True

        await self.mtcs.slew_icrs(
            ra=self.config.ra,
            dec=self.config.dec,
            rot=self.config.rot_sky,
            rot_type=RotType.Sky,
            target_name=self.config.name,
        )

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
            await self.gencam.take_object(
                exptime=exptime,
                group_id=self.group_id,
                reason=self.config.reason,
                program=self.config.program,
            )

    async def stop_tracking(self):
        """Execute stop tracking on MTCS."""
        await self.mtcs.stop_tracking()
