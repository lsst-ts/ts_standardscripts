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

import asyncio
import copy
import random
import logging
import unittest
import contextlib

import pytest

from lsst.ts import salobj
from lsst.ts.observatory.control.utils import RotType
from lsst.ts import standardscripts
from lsst.ts.standardscripts.auxtel import TrackTargetAndTakeImage

random.seed(47)  # for set_random_lsst_dds_partition_prefix

logging.basicConfig()


class TestAuxTelTrackTargetAndTakeImage(
    standardscripts.BaseScriptTestCase, unittest.IsolatedAsyncioTestCase
):
    """Test Auxiliary Telescope track target script.

    Both AT and MT Slew scripts uses the same base script class. This unit
    test performs the basic checks on Script integrity. For a more detailed
    unit testing routine check the MT version.
    """

    @classmethod
    def setUpClass(cls) -> None:
        cls.log = logging.getLogger("TestAuxTelTrackTargetAndTakeImage")
        return super().setUpClass()

    async def basic_make_script(self, index):
        self.script = TrackTargetAndTakeImage(index=index, add_remotes=False)

        return (self.script,)

    async def test_configure(self):
        async with self.make_script():

            configuration_full = await self.configure_script_full()

            for key in configuration_full:
                assert configuration_full[key] == getattr(self.script.config, key)

            required_fields = {
                "ra",
                "dec",
                "rot_sky",
                "name",
                "obs_time",
                "num_exp",
                "exp_times",
                "band_filter",
                "grating",
            }

            for required_field in required_fields:
                bad_configuration = copy.deepcopy(configuration_full)
                bad_configuration.pop(required_field)
                with pytest.raises(salobj.ExpectedError):
                    await self.configure_script(**bad_configuration)

    async def test_run(self):

        async with self.make_script(), self.setup_mocks():

            self.script.atcs.check_tracking.side_effect = (
                self.check_tracking_forever_side_effect
            )

            configuration_full = await self.configure_script_full()

            await self.run_script()

            self.script.atcs.slew_icrs.assert_awaited_once_with(
                ra=configuration_full["ra"],
                dec=configuration_full["dec"],
                rot=configuration_full["rot_sky"],
                rot_type=RotType.Sky,
                target_name=configuration_full["name"],
            )
            self.script.latiss.setup_atspec.assert_awaited_once_with(
                grating=configuration_full["grating"],
                filter=configuration_full["band_filter"],
            )
            latiss_take_object_calls = [
                unittest.mock.call(
                    exptime=exptime,
                    group_id=self.script.group_id,
                    grating=configuration_full["grating"],
                    filter=configuration_full["band_filter"],
                    reason=configuration_full["reason"],
                    program=configuration_full["program"],
                )
                for exptime in configuration_full["exp_times"]
            ]

            self.script.latiss.take_object.assert_has_awaits(latiss_take_object_calls)
            self.script.atcs.check_tracking.assert_awaited_once()

            self.script.atcs.stop_tracking.assert_not_awaited()

    async def test_run_multiple_filters(self):

        async with self.make_script(), self.setup_mocks():

            self.script.atcs.check_tracking.side_effect = (
                self.check_tracking_forever_side_effect
            )

            configuration_full = await self.configure_script_full(
                band_filter=["g", "r"], grating=["empty_1", "empty_2"]
            )

            await self.run_script()

            self.script.atcs.slew_icrs.assert_awaited_once_with(
                ra=configuration_full["ra"],
                dec=configuration_full["dec"],
                rot=configuration_full["rot_sky"],
                rot_type=RotType.Sky,
                target_name=configuration_full["name"],
            )
            self.script.latiss.setup_atspec.assert_awaited_once_with(
                grating=configuration_full["grating"][0],
                filter=configuration_full["band_filter"][0],
            )
            latiss_take_object_calls = [
                unittest.mock.call(
                    exptime=exptime,
                    group_id=self.script.group_id,
                    grating=grating,
                    filter=band_filter,
                    reason=configuration_full["reason"],
                    program=configuration_full["program"],
                )
                for exptime, grating, band_filter in zip(
                    configuration_full["exp_times"],
                    configuration_full["grating"],
                    configuration_full["band_filter"],
                )
            ]

            self.script.latiss.take_object.assert_has_awaits(latiss_take_object_calls)
            self.script.atcs.check_tracking.assert_awaited_once()

            self.script.atcs.stop_tracking.assert_not_awaited()

    async def test_run_fail_setup_atspec(self):

        async with self.make_script(), self.setup_mocks():

            self.script.latiss.setup_atspec.side_effect = RuntimeError(
                "Setup atspec failed"
            )

            configuration_full = await self.configure_script_full()

            with pytest.raises(AssertionError):
                await self.run_script()

            self.script.atcs.slew_icrs.assert_awaited_once_with(
                ra=configuration_full["ra"],
                dec=configuration_full["dec"],
                rot=configuration_full["rot_sky"],
                rot_type=RotType.Sky,
                target_name=configuration_full["name"],
            )
            self.script.latiss.setup_atspec.assert_awaited_once_with(
                grating=configuration_full["grating"],
                filter=configuration_full["band_filter"],
            )

            self.script.latiss.take_object.assert_not_awaited()
            self.script.atcs.check_tracking.assert_not_awaited()

            self.script.atcs.stop_tracking.assert_awaited_once()

    async def test_run_fail_slew(self):

        async with self.make_script(), self.setup_mocks():

            self.script.atcs.slew_icrs.side_effect = RuntimeError("Slew failed")

            configuration_full = await self.configure_script_full()

            with pytest.raises(AssertionError):
                await self.run_script()

            self.script.atcs.slew_icrs.assert_awaited_once_with(
                ra=configuration_full["ra"],
                dec=configuration_full["dec"],
                rot=configuration_full["rot_sky"],
                rot_type=RotType.Sky,
                target_name=configuration_full["name"],
            )
            self.script.latiss.setup_atspec.assert_awaited_once_with(
                grating=configuration_full["grating"],
                filter=configuration_full["band_filter"],
            )

            self.script.latiss.take_object.assert_not_awaited()
            self.script.atcs.check_tracking.assert_not_awaited()

            self.script.atcs.stop_tracking.assert_awaited_once()

    async def test_run_fail_check_tracking(self):

        async with self.make_script(), self.setup_mocks():

            self.script.atcs.check_tracking.side_effect = (
                self.check_tracking_fail_after_1s_side_effect
            )

            configuration_full = await self.configure_script_full()

            with pytest.raises(AssertionError):
                await self.run_script()

            self.script.atcs.slew_icrs.assert_awaited_once_with(
                ra=configuration_full["ra"],
                dec=configuration_full["dec"],
                rot=configuration_full["rot_sky"],
                rot_type=RotType.Sky,
                target_name=configuration_full["name"],
            )
            self.script.latiss.setup_atspec.assert_awaited_once_with(
                grating=configuration_full["grating"],
                filter=configuration_full["band_filter"],
            )
            latiss_take_object_calls = [
                unittest.mock.call(
                    exptime=configuration_full["exp_times"][0],
                    group_id=self.script.group_id,
                    grating=configuration_full["grating"],
                    filter=configuration_full["band_filter"],
                    reason=configuration_full["reason"],
                    program=configuration_full["program"],
                ),
            ]

            self.script.latiss.take_object.assert_has_awaits(latiss_take_object_calls)
            self.script.atcs.check_tracking.assert_awaited_once()

            self.script.atcs.stop_tracking.assert_awaited_once()

    async def test_executable(self):
        scripts_dir = standardscripts.get_scripts_dir()
        script_path = scripts_dir / "auxtel" / "track_target_and_take_image.py"
        await self.check_executable(script_path)

    @contextlib.asynccontextmanager
    async def setup_mocks(self):
        self.script.atcs.slew_icrs = unittest.mock.AsyncMock()
        self.script.atcs.stop_tracking = unittest.mock.AsyncMock()
        self.script.atcs.check_tracking = unittest.mock.AsyncMock()
        self.script.latiss.setup_atspec = unittest.mock.AsyncMock()
        self.script.latiss.take_object = unittest.mock.AsyncMock(
            side_effect=self.take_object_side_effect
        )

        yield

    async def configure_script_full(self, band_filter="r", grating="empty_1"):
        configuration_full = dict(
            targetid=10,
            ra="10:00:00",
            dec="-10:00:00",
            rot_sky=0.0,
            name="unit_test_target",
            obs_time=7.0,
            estimated_slew_time=5.0,
            num_exp=2,
            exp_times=[2.0, 1.0],
            band_filter=band_filter,
            grating=grating,
            reason="Unit testing",
            program="UTEST",
        )

        await self.configure_script(**configuration_full)

        return configuration_full

    async def check_tracking_forever_side_effect(self):
        """Emulates a check tracking routine."""
        self.log.debug("Wait for ever.")
        future = asyncio.Future()
        await future

    async def check_tracking_fail_after_1s_side_effect(self):

        self.log.debug("Wait 1 second and raise runtime error.")
        await asyncio.sleep(1.0)
        raise RuntimeError("Check tracking failed.")

    async def take_object_side_effect(
        self,
        exptime,
        filter,
        grating,
        group_id,
        reason,
        program,
    ):

        self.log.debug(
            f"exptime: {exptime}s, group_id: {group_id}, reason: {reason}, program: {program}"
        )
        await asyncio.sleep(exptime)


if __name__ == "__main__":
    unittest.main()
