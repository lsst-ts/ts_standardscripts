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

import unittest
from unittest.mock import Mock

from lsst.ts.standardscripts import BaseScriptTestCase, get_scripts_dir
from lsst.ts.standardscripts.wait_for_sun_elevation import WaitForSunElevation


class TestWaitForSunElevation(BaseScriptTestCase, unittest.IsolatedAsyncioTestCase):
    async def basic_make_script(self, index):
        self.script = WaitForSunElevation(index=index)
        self.script.estimate_duration = Mock(return_value=120.0)
        return (self.script,)

    async def test_configure_defaults(self):
        async with self.make_script():
            await self.configure_script()

            self.assertEqual(self.script.target_elevation, -10.0)
            self.assertEqual(self.script.poll_interval, 5.0)

    async def test_configure_custom(self):
        async with self.make_script():
            await self.configure_script(target_elevation=-18.0, poll_interval=30.0)

            self.assertEqual(self.script.target_elevation, -18.0)
            self.assertEqual(self.script.poll_interval, 30.0)

    async def test_run_sun_already_below_target(self):
        """Script exits immediately when sun is already at or below target."""
        async with self.make_script():
            await self.configure_script(target_elevation=-10.0, poll_interval=1.0)
            self.script.get_sun_azel = Mock(return_value=(180.0, -15.0))
            await self.run_script()

    async def test_run_sun_descends_to_target(self):
        """Script loops until the sun descends through the target elevation."""
        async with self.make_script():
            await self.configure_script(target_elevation=-10.0, poll_interval=1.0)
            self.script.get_sun_azel = Mock(
                side_effect=[
                    (180.0, -8.0),
                    (180.0, -9.5),
                    (180.0, -10.5),
                ]
            )
            await self.run_script()

    async def test_run_sun_already_at_target(self):
        """Script exits immediately when elevation equals the target."""
        async with self.make_script():
            await self.configure_script(target_elevation=-10.0, poll_interval=1.0)
            self.script.get_sun_azel = Mock(return_value=(180.0, -10.0))
            await self.run_script()

    async def test_executable(self):
        scripts_dir = get_scripts_dir()
        script_path = scripts_dir / "wait_for_sun_elevation.py"
        await self.check_executable(script_path)


if __name__ == "__main__":
    unittest.main()
