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

from lsst.ts import standardscripts
from lsst.ts.observatory.control.utils import RotType
from lsst.ts.standardscripts.auxtel import TrackTarget

random.seed(47)  # for set_random_lsst_dds_partition_prefix

logging.basicConfig()


class TestATTrackTarget(
    standardscripts.BaseScriptTestCase, unittest.IsolatedAsyncioTestCase
):
    """Test Auxiliary Telescope track target script.

    Both AT and MT Slew scripts uses the same base script class. This unit
    test performs the basic checks on Script integrity. For a more detailed
    unit testing routine check the MT version.
    """

    async def basic_make_script(self, index):
        self.script = TrackTarget(index=index)

        return (self.script,)

    async def test_run_slew_target_name(self):

        async with self.make_script():

            self.script.tcs.slew_icrs = unittest.mock.AsyncMock()
            self.script.tcs.slew_object = unittest.mock.AsyncMock()
            self.script.tcs.stop_tracking = unittest.mock.AsyncMock()

            # Check running with target_name only
            await self.configure_script(target_name="eta Car")

            await self.run_script()

            self.assert_slew_target_name()

    async def test_run_slew_radec(self):

        async with self.make_script():

            self.script.tcs.slew_icrs = unittest.mock.AsyncMock()
            self.script.tcs.slew_object = unittest.mock.AsyncMock()
            self.script.tcs.stop_tracking = unittest.mock.AsyncMock()

            self.script.tcs.slew_object.reset_mock()
            self.script.tcs.slew_icrs.reset_mock()

            # Check running with ra dec only
            config = dict(slew_icrs=dict(ra=1.0, dec=-10.0))

            await self.configure_script(**config)

            await self.run_script()

            self.assert_slew_radec()

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

    async def test_executable(self):
        scripts_dir = standardscripts.get_scripts_dir()
        script_path = scripts_dir / "auxtel" / "track_target.py"
        await self.check_executable(script_path)

    def assert_slew_radec(self):

        self.script.tcs.slew_icrs.assert_awaited_once()
        self.script.tcs.slew_object.assert_not_awaited()
        self.script.tcs.stop_tracking.assert_not_awaited()

    def assert_slew_target_name(self):
        self.script.tcs.slew_object.assert_awaited_once()
        self.script.tcs.slew_object.assert_awaited_with(
            name="eta Car",
            rot=0.0,
            rot_type=RotType.SkyAuto,
            offset_x=0.0,
            offset_y=0.0,
        )
        self.script.tcs.slew_icrs.assert_not_awaited()
        self.script.tcs.stop_tracking.assert_not_awaited()

    def assert_slew_azel(self, find_target_config):

        self.script.tcs.find_target.assert_awaited_once()
        self.script.tcs.find_target.assert_awaited_with(**find_target_config)
        self.assert_slew_target_name()


if __name__ == "__main__":
    unittest.main()
