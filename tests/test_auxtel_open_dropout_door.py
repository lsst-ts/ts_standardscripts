# This file is part of ts_auxtel_standardscripts
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
import types
import unittest

import pytest
from lsst.ts import standardscripts
from lsst.ts.auxtel.standardscripts import get_scripts_dir
from lsst.ts.auxtel.standardscripts.atdome import OpenDropoutDoor


class TestOpenDropoutDoor(
    standardscripts.BaseScriptTestCase, unittest.IsolatedAsyncioTestCase
):
    async def basic_make_script(self, index):
        # Create an instance of the script.
        self.script = OpenDropoutDoor(index=index)

        self.script.atcs = unittest.mock.MagicMock()
        self.script.atcs.open_dropout_door = unittest.mock.AsyncMock()
        self.script.ess_remote = unittest.mock.MagicMock()
        self.script.ess_remote.tel_airFlow = unittest.mock.MagicMock()

        return (self.script,)

    def setUp(self):
        super().setUp()
        self.normal_wind = types.SimpleNamespace(speed=5, maxSpeed=7, speedStdDev=1)
        self.gusty_wind = types.SimpleNamespace(speed=5, maxSpeed=12, speedStdDev=4)
        self.high_wind = types.SimpleNamespace(speed=9, maxSpeed=11, speedStdDev=2)
        self.unstable_data = types.SimpleNamespace(speed=8, maxSpeed=10, speedStdDev=6)

    async def setup_wind_speed(self, wind_data):
        """Mock the wind data directly."""
        self.script.ess_remote.tel_airFlow.next = unittest.mock.AsyncMock(
            return_value=wind_data
        )

    async def test_run_script_with_normal_conditions(self):
        async with self.make_script():
            await self.setup_wind_speed(self.normal_wind)
            await self.configure_script()
            await self.run_script()
            self.script.atcs.open_dropout_door.assert_awaited_once()

    async def test_run_script_with_gusty_conditions(self):
        async with self.make_script():
            await self.setup_wind_speed(self.gusty_wind)
            await self.configure_script()
            with pytest.raises(AssertionError):
                await self.run_script()
            self.script.atcs.open_dropout_door.assert_not_awaited()

    async def test_run_script_with_high_wind(self):
        async with self.make_script():
            await self.setup_wind_speed(self.high_wind)
            await self.configure_script()
            with pytest.raises(AssertionError):
                await self.run_script()
            self.script.atcs.open_dropout_door.assert_not_awaited()

    async def test_run_script_with_unstable_data(self):
        async with self.make_script():
            await self.setup_wind_speed(self.unstable_data)
            await self.configure_script()
            with pytest.raises(AssertionError):
                await self.run_script()
            self.script.atcs.open_dropout_door.assert_not_awaited()

    async def test_run_script_cannot_determine_wind_speed(self):
        async with self.make_script():
            self.script.ess_remote.tel_airFlow.next = unittest.mock.AsyncMock(
                side_effect=asyncio.TimeoutError
            )

            await self.configure_script()
            with self.assertLogs(level="WARNING") as log:
                await self.run_script()

            # Ensure the warning message about wind speed is logged
            expected_message = (
                "Cannot determine wind speed. Proceeding with caution. "
                "Ensure it is safe to open."
            )
            found = any(expected_message in message for message in log.output)
            self.assertTrue(
                found, f"Expected log message not found. Log output: {log.output}"
            )

            # Make sure it was not awaited
            self.script.atcs.open_dropout_door.assert_awaited_once()

    async def test_executable(self):
        scripts_dir = get_scripts_dir()
        script_path = scripts_dir / "atdome" / "open_dropout_door.py"
        await self.check_executable(script_path)
