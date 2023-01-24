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

import logging
import random
import unittest

import pytest
from lsst.ts.idl.enums.MTPtg import WrapStrategy
from lsst.ts.observatory.control import RotType

from lsst.ts import salobj, standardscripts
from lsst.ts.standardscripts.maintel import TrackTarget

random.seed(47)  # for set_random_lsst_dds_partition_prefix

logging.basicConfig()


class TestMTSlew(standardscripts.BaseScriptTestCase, unittest.IsolatedAsyncioTestCase):
    async def basic_make_script(self, index):
        self.script = TrackTarget(index=index)

        return (self.script,)

    async def test_configure(self):
        """Test different configuration scenarios."""
        async with self.make_script():
            # Test no default configuration. User must provide something.
            with pytest.raises(salobj.ExpectedError):
                await self.configure_script()

        async with self.make_script():
            # If RA is given Dec must be given too.
            with pytest.raises(salobj.ExpectedError):
                await self.configure_script(slew_icrs=dict(ra=10.0))

        async with self.make_script():
            # If Dec is given ra must be given too.
            with pytest.raises(salobj.ExpectedError):
                await self.configure_script(slew_icrs=dict(dec=-10.0))

        async with self.make_script():
            # Invalid RA
            with pytest.raises(salobj.ExpectedError):
                await self.configure_script(slew_icrs=dict(ra=-0.1, dec=0.0))

        async with self.make_script():
            # Invalid RA
            with pytest.raises(salobj.ExpectedError):
                await self.configure_script(slew_icrs=dict(ra=24.1, dec=0.0))

        async with self.make_script():
            # Invalid Dec
            with pytest.raises(salobj.ExpectedError):
                await self.configure_script(slew_icrs=dict(ra=1.0, dec=-90.1))

        async with self.make_script():
            # Invalid Dec
            with pytest.raises(salobj.ExpectedError):
                await self.configure_script(slew_icrs=dict(ra=1.0, dec=90.1))

        async with self.make_script():
            # Invalid rot_type
            with pytest.raises(salobj.ExpectedError):
                await self.configure_script(
                    slew_icrs=dict(
                        ra=1.0,
                        dec=-10.0,
                    ),
                    rot_type="invalid",
                )

        async with self.make_script():
            # Script can be configured with target name only
            await self.configure_script(target_name="eta Car")

        async with self.make_script():
            # Script can be configured with ra, dec only
            await self.configure_script(slew_icrs=dict(ra=1.0, dec=-10.0))

        async with self.make_script():
            # Script can be configured with az/el
            await self.configure_script(
                find_target=dict(az=1.0, el=80.0, mag_limit=8.0)
            )

        # Configure passing rotator angle and all rotator strategies
        for rot_type in RotType:
            with self.subTest(f"rot_type={rot_type.name}", rot_type=rot_type.name):
                async with self.make_script():
                    await self.configure_script(
                        slew_icrs=dict(ra=1.0, dec=-10.0),
                        rot_value=10,
                        rot_type=rot_type.name,
                    )

        async with self.make_script():
            # Test ignore feature.
            await self.configure_script(
                target_name="eta Car", ignore=["mtdometrajectory", "mthexapod_1"]
            )

            assert not self.script.tcs.check.mtdometrajectory
            assert not self.script.tcs.check.mthexapod_1

        # Configure passing az_wrap_strategy
        for az_wrap_strategy in WrapStrategy:
            with self.subTest(f"az_wrap_strategy={az_wrap_strategy.name}"):
                async with self.make_script():
                    await self.configure_script(
                        slew_icrs=dict(ra=1.0, dec=-10.0),
                        az_wrap_strategy=az_wrap_strategy.name,
                    )
                    assert self.script.config.az_wrap_strategy == az_wrap_strategy

    async def test_run_slew_target_name(self):

        async with self.make_script():

            self.script.tcs.slew_icrs = unittest.mock.AsyncMock()
            self.script.tcs.slew_object = unittest.mock.AsyncMock()
            self.script.tcs.stop_tracking = unittest.mock.AsyncMock()

            # Check running with target_name only
            await self.configure_script(target_name="eta Car")

            await self.run_script()

            self.assert_slew_target_name()

    async def test_run_slew_azel(self):
        async with self.make_script():

            self.script.tcs.slew_icrs = unittest.mock.AsyncMock()
            self.script.tcs.slew_object = unittest.mock.AsyncMock()
            self.script.tcs.find_target = unittest.mock.AsyncMock(
                return_value="eta Car"
            )
            self.script.tcs.stop_tracking = unittest.mock.AsyncMock()

            self.script.tcs.slew_object.reset_mock()
            self.script.tcs.slew_icrs.reset_mock()

            # Check running with ra dec only
            config = dict(find_target=dict(az=0.0, el=80.0, mag_limit=1.0))

            await self.configure_script(**config)

            await self.run_script()

            self.assert_slew_azel(find_target_config=config["find_target"])

    async def test_run_slew_radec(self):

        async with self.make_script():

            self.script.tcs.slew_icrs = unittest.mock.AsyncMock()
            self.script.tcs.slew_object = unittest.mock.AsyncMock()
            self.script.tcs.stop_tracking = unittest.mock.AsyncMock()

            # Check running with ra dec only
            await self.configure_script(slew_icrs=dict(ra=1.0, dec=-10.0))

            await self.run_script()

            self.assert_slew_radec()

    async def test_run_slew_fails(self):

        async with self.make_script():

            self.script.tcs.slew_icrs = unittest.mock.AsyncMock(
                side_effect=RuntimeError
            )
            self.script.tcs.slew_object = unittest.mock.AsyncMock()
            self.script.tcs.stop_tracking = unittest.mock.AsyncMock()

            # Check running with ra dec only
            await self.configure_script(slew_icrs=dict(ra=1.0, dec=-10.0))

            with pytest.raises(AssertionError):
                await self.run_script()

            self.assert_slew_fails()

    async def test_executable(self):
        scripts_dir = standardscripts.get_scripts_dir()
        script_path = scripts_dir / "maintel" / "track_target.py"
        await self.check_executable(script_path)

    def assert_slew_radec(self):

        self.script.tcs.slew_icrs.assert_awaited_once()
        self.script.tcs.slew_icrs.assert_awaited_with(
            ra=self.script.config.slew_icrs["ra"],
            dec=self.script.config.slew_icrs["dec"],
            rot=self.script.config.rot_value,
            rot_type=self.script.config.rot_type,
            target_name=getattr(self.script.config, "target_name", "slew_icrs"),
            dra=self.script.config.differential_tracking["dra"],
            ddec=self.script.config.differential_tracking["ddec"],
            offset_x=self.script.config.offset["x"],
            offset_y=self.script.config.offset["y"],
            az_wrap_strategy=self.script.config.az_wrap_strategy,
            time_on_target=self.script.config.track_for,
        )
        self.script.tcs.slew_object.assert_not_awaited()
        self.script.tcs.stop_tracking.assert_not_awaited()

    def assert_slew_target_name(self):
        self.script.tcs.slew_object.assert_awaited_once()
        self.script.tcs.slew_object.assert_awaited_with(
            name="eta Car",
            rot=0.0,
            rot_type=RotType.SkyAuto,
            dra=0.0,
            ddec=0.0,
            offset_x=0.0,
            offset_y=0.0,
            az_wrap_strategy=self.script.tcs.WrapStrategy.OPTIMIZE,
            time_on_target=0.0,
        )
        self.script.tcs.slew_icrs.assert_not_awaited()
        self.script.tcs.stop_tracking.assert_not_awaited()

    def assert_slew_azel(self, find_target_config):

        self.script.tcs.find_target.assert_awaited_once()
        self.script.tcs.find_target.assert_awaited_with(**find_target_config)
        self.assert_slew_target_name()

    def assert_slew_fails(self):
        self.script.tcs.slew_icrs.assert_awaited_once()
        self.script.tcs.slew_object.assert_not_awaited()
        self.script.tcs.stop_tracking.assert_awaited_once()


if __name__ == "__main__":
    unittest.main()
