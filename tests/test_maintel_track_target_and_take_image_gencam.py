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

import asyncio
import contextlib
import copy
import logging
import random
import types
import unittest

import numpy
import pytest
from lsst.ts import salobj, standardscripts
from lsst.ts.maintel.standardscripts.track_target_and_take_image_gencam import (
    TrackTargetAndTakeImageGenCam,
)
from lsst.ts.observatory.control.utils import RotType

random.seed(42)  # for set_random_lsst_dds_partition_prefix

logging.basicConfig()


class TestMainTelTrackTargetAndTakeImageGenCam(
    standardscripts.BaseScriptTestCase, unittest.IsolatedAsyncioTestCase
):
    """
    Test Main Telescope track target and take image with GenCam script.

    Both AT and MT Slew scripts uses the same base script class. This unit
    test performs the basic checks on Script integrity. For a more detailed
    unit testing routine check the MT version.
    """

    @classmethod
    def setUpClass(cls) -> None:
        cls.log = logging.getLogger("TestMainTelTrackTargetAndTakeImageGenCam")
        return super().setUpClass()

    def setUp(self) -> None:
        self.rotator_position = 0.0  # deg
        self.rotator_velocity = 10.0  # deg/s
        self.rot_sky_emulate_zero = 45.0
        self._handle_slew_calls = 0
        self._fail_handle_slew_after = 0
        return super().setUp()

    async def basic_make_script(self, index):
        self.script = TrackTargetAndTakeImageGenCam(index=index, add_remotes=False)
        return (self.script,)

    async def check_tracking_fail_after_1s_side_effect(self):
        self.log.debug("Wait 1 second and raise runtime error.")
        await asyncio.sleep(1.0)
        raise RuntimeError("Check tracking failed.")

    async def check_tracking_forever_side_effect(self):
        """Emulates a check tracking routine."""
        self.log.debug("Wait for ever.")
        future = asyncio.Future()
        await future

    async def configure_script_full(
        self,
        generic_camera: list | None = None,
    ) -> None:
        if generic_camera is None:
            generic_camera = [
                dict(
                    index=random.randint(1, 10),
                    exp_times=[random.randint(1, 10) for _ in range(2)],
                ),
            ]

        configuration_full = dict(
            targetid=10,
            ra="10:00:00",
            dec="-10:00:00",
            rot_sky=0.0,
            name="unit_test_target",
            obs_time=7.0,
            estimated_slew_time=5.0,
            # Instead of num_exp, the number of exposures is definve by the
            #  number of elements in generic_camera.exp_times.
            num_exp=2,
            # exp_times is ignored in this script.
            #  Use generic_camera.exp_times instead.
            exp_times=[0, 0],
            reason="Unit testing",
            program="UTEST",
            generic_camera=generic_camera,
            band_filter="",
        )

        await self.configure_script(**configuration_full)
        self.log.debug(f"Parsed configuration:\n {self.script.config}")

        return configuration_full

    async def get_rotator_position(self, flush, timeout):
        if flush:
            await asyncio.sleep(timeout / 2.0)
        return types.SimpleNamespace(actualPosition=self.rotator_position)

    async def handle_slew_icrs(
        self,
        rot,
        rot_type,
        **kwargs,
    ):
        self._handle_slew_calls += 1
        if (
            self._fail_handle_slew_after > 0
            and self._handle_slew_calls > self._fail_handle_slew_after
        ):
            raise RuntimeError(
                f"Failing slew after {self._fail_handle_slew_after} calls."
            )
        await asyncio.sleep(0.5)
        if rot_type == RotType.Physical:
            self.log.debug(f"Slew with rot_type = {RotType.Physical!r}")
            rotator_velocity = self.rotator_velocity * (
                1.0 if rot > self.rotator_position else -1.0
            )
            rotator_positions = numpy.arange(
                self.rotator_position, rot, rotator_velocity
            )
            for _rot in rotator_positions:
                self.log.debug(f"Rotator position: {self.rotator_position} -> {_rot}")
                self.rotator_position = _rot
                await asyncio.sleep(1.0)
            self.rotator_position = rot
        else:
            self.rotator_position = rot + self.rot_sky_emulate_zero
        await asyncio.sleep(0.5)

    @contextlib.asynccontextmanager
    async def setup_mocks(self):
        self.script.mtcs.slew_icrs = unittest.mock.AsyncMock(
            side_effect=self.handle_slew_icrs
        )
        self.script.mtcs.stop_tracking = unittest.mock.AsyncMock()
        self.script.mtcs.check_tracking = unittest.mock.AsyncMock()
        self.script.mtcs.rem = types.SimpleNamespace(
            mtrotator=unittest.mock.AsyncMock()
        )

        for cam in self.script.gencam:
            cam.take_object = unittest.mock.AsyncMock(
                side_effect=self.take_object_side_effect
            )

        self.script.mtcs.rem.mtrotator.configure_mock(
            **{"tel_rotation.next.side_effect": self.get_rotator_position}
        )

        yield

    async def take_object_side_effect(
        self,
        exptime,
        group_id,
        reason,
        program,
    ):
        self.log.debug(
            f"exptime: {exptime}s, group_id: {group_id}, reason: {reason}, program: {program}"
        )
        await asyncio.sleep(exptime)

    async def test_configure_single_camera(self):
        """Test a successful configuration for a single camera"""
        async with self.make_script():
            configuration_full = await self.configure_script_full()
            self.log.debug(configuration_full)

            # Try/Except help identify which key is not matching
            try:
                for key in configuration_full:
                    if key == "exp_times":
                        continue
                    assert configuration_full[key] == getattr(self.script.config, key)
            except AssertionError as err:
                raise AssertionError(
                    f"Configuration for {key} does not match."
                ) from err

    async def test_configure_bad(self) -> None:
        """Test a bad configuration for a single camera"""
        async with self.make_script():
            configuration_full = await self.configure_script_full()

            required_fields = {
                "ra",
                "dec",
                "rot_sky",
                "name",
                "obs_time",
                "num_exp",
                "exp_times",
                "generic_camera",
                "band_filter",
            }

            for required_field in required_fields:
                bad_configuration = copy.deepcopy(configuration_full)
                bad_configuration.pop(required_field)
                with pytest.raises(salobj.ExpectedError):
                    await self.configure_script(**bad_configuration)

    async def test_configure_multiple_cameras(self) -> None:
        """Test a successful configuration for multiple cameras"""
        async with self.make_script():
            configuration_full = await self.configure_script_full(
                generic_camera=[
                    dict(
                        index=random.randint(1, 10),
                        exp_times=[random.randint(1, 10) for _ in range(2)],
                    )
                    for _ in range(3)
                ]
            )

            self.log.debug(configuration_full)

            # Try/Except help identify which key is not matching
            try:
                for key in configuration_full:
                    if key == "exp_times":
                        continue
                    assert configuration_full[key] == getattr(self.script.config, key)
            except AssertionError as err:
                raise AssertionError(
                    f"Configuration for {key} does not match."
                ) from err

    async def test_executable(self):
        scripts_dir = standardscripts.get_scripts_dir()
        script_path = scripts_dir / "maintel" / "track_target_and_take_image_gencam.py"
        await self.check_executable(script_path)

    async def test_run_fail_check_tracking(self):
        async with self.make_script():
            # New GemCam is stanciated during configuration
            configuration_full = await self.configure_script_full()

            async with self.setup_mocks():
                self.script.mtcs.check_tracking.side_effect = (
                    self.check_tracking_fail_after_1s_side_effect
                )

                self.rotator_position = -15.0

                with pytest.raises(AssertionError):
                    await self.run_script()

                slew_icrs_expected_calls = [
                    unittest.mock.call(
                        ra=configuration_full["ra"],
                        dec=configuration_full["dec"],
                        rot=configuration_full["rot_sky"],
                        rot_type=RotType.Sky,
                        target_name=configuration_full["name"],
                        az_wrap_strategy=self.script.config.az_wrap_strategy,
                        time_on_target=self.script.get_estimated_time_on_target(),
                    ),
                ]

                self.script.mtcs.slew_icrs.assert_has_awaits(slew_icrs_expected_calls)

                for i, cam in enumerate(self.script.gencam):
                    gencam_dict = configuration_full["generic_camera"][i]
                    gencam_take_object_calls = [
                        unittest.mock.call(
                            exptime=gencam_dict["exp_times"][0],
                            group_id=self.script.group_id,
                            reason=configuration_full["reason"],
                            program=configuration_full["program"],
                        )
                    ]
                    cam.take_object.assert_has_awaits(gencam_take_object_calls)

                self.script.mtcs.check_tracking.assert_awaited_once()

                self.script.mtcs.stop_tracking.assert_awaited_once()


if __name__ == "__main__":
    unittest.main()
