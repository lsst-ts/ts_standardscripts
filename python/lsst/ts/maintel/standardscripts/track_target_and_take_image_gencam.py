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

__all__ = ["TrackTargetAndTakeImageGenCam"]

import asyncio

from lsst.ts.observatory.control import Usages
from lsst.ts.observatory.control.generic_camera import GenericCamera
from lsst.ts.observatory.control.maintel.mtcs import MTCS, MTCSUsages
from lsst.ts.observatory.control.utils import RotType
from lsst.ts.standardscripts.base_track_target_and_take_image import (
    BaseTrackTargetAndTakeImage,
)


class TrackTargetAndTakeImageGenCam(BaseTrackTargetAndTakeImage):
    """Track target and take image script with one more Generic Cameras.

    This script implements a simple visit consistig of slewing to a target,
    start tracking and take image.

    This class configuration is inherited from ``BaseTrackTargetAndTakeImage``.
    The only applied changes are:

    - The addition of the ``generic_camera`` configuration parameter.
      This parameter is a list of objects with the following structure:
        - ``index``: Index of the Generic Camera SAL component.
        - ``exp_times``: Exposure times (seconds) for each camera.

    - The ``exp_times`` and ``num_exp`` parameters are ignored by this script.
      However, we keep them to keep compatibility with the Scheduler.
      Instead, use the ``exp_times`` parameter in the ``generic_camera``.

    See below for an example of configuration.

    Parameters
    ----------
    index : `int`
        Index of Script SAL component.
    add_remotes : `bool` (optional)
        Create remotes to control components (default: `True`)? If False, the
        script will not work for normal operations. Useful for unit testing.

    Examples
    --------
    Here is an example of configuration for this script:

    .. code-block:: yaml

        targetid: MY_TARGET_ID
        ra: "10:00:00"
        dec: "-10:00:00"
        rot_sky: 0.0
        name: "config_example_target"
        obs_time: 1.0
        estimated_slew_time: 5.0
        num_exp: 2
        exp_times: [0]
        reason: "Configuration Example"
        program: "CFG_EXAMPLE"
        generic_camera:
            - index: 101
              exp_times: [2.5, 2.5, 2.5]
            - index: 102
              exp_times: [5, 5]
        band_filter: ""

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

        self.mtcs = MTCS(
            domain=self.domain,
            log=self.log,
            intended_usage=self.mtcs_usage,
        )

        self.gencam = None

        self.instrument_name = "GenCam"

    @property
    def tcs(self):
        return self.mtcs

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
            *(gencam.assert_all_enabled() for gencam in self.gencam),
            *(gencam.assert_liveliness() for gencam in self.gencam),
        )

    def get_instrument_name(self):
        return self.instrument_name

    async def configure(self, config):
        await super().configure(config)

        self.gencam = [
            GenericCamera(
                gencam["index"],
                domain=self.domain,
                log=self.log,
                intended_usage=self.gencam_usage,
            )
            for gencam in self.config.generic_camera
        ]

    @classmethod
    def get_schema(cls):
        schema_dict = cls.get_base_schema()
        schema_dict["$id"] = (
            "https://github.com/lsst-ts/ts_standardscripts/maintel/track_target_and_take_image_gencam.py"
        )
        schema_dict["title"] = "TrackTargetAndTakeImageGenCam v1"
        schema_dict["description"] = "Configuration for TrackTargetAndTakeImageGenCam."

        schema_dict["properties"]["generic_camera"] = dict(
            type="array",
            description="Information associated with the Generic Cameras",
            minItems=1,
            index=dict(
                type="integer",
                description="Index of the Generic Camera SAL component.",
            ),
            exp_times=dict(
                type="array",
                description="Exposure times (seconds) for each camera.",
                items=dict(
                    type="number",
                    minimum=0,
                ),
            ),
        )

        schema_dict["properties"]["exp_times"]["description"] = (
            "Exposure times (seconds). Ignored by the Generic Cameras. "
            "Kept only for code compatibility."
        )

        schema_dict["required"].append("generic_camera")

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
            az_wrap_strategy=self.config.az_wrap_strategy,
            time_on_target=self.get_estimated_time_on_target(),
        )

    async def take_data(self):
        """Take data while making sure ATCS is tracking."""
        tasks = [
            asyncio.create_task(self._take_data(idx))
            for idx, _ in enumerate(self.gencam)
        ]
        tasks.append(asyncio.create_task(self.mtcs.check_tracking()))
        await self.mtcs.process_as_completed(tasks)

    async def _take_data(self, cam_arr_index):
        """
        Take data.

        Parameters
        ----------
        cam_arr_index : int
            Camera array index. This is used to index the ``generic_camera``.
        """

        for exptime in self.config.generic_camera[cam_arr_index]["exp_times"]:
            await self.gencam[cam_arr_index].take_object(
                exptime=exptime,
                group_id=self.group_id,
                reason=self.config.reason,
                program=self.config.program,
            )

    async def stop_tracking(self):
        """Execute stop tracking on MTCS."""
        await self.mtcs.stop_tracking()
