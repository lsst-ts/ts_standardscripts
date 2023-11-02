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

from lsst.ts.standardscripts import BaseScriptTestCase, get_scripts_dir
from lsst.ts.standardscripts.sleep import Sleep


class TestSleep(BaseScriptTestCase, unittest.IsolatedAsyncioTestCase):
    async def basic_make_script(self, index):
        self.script = Sleep(index=index)
        return (self.script,)

    async def test_configure(self):
        # Test that the sleep time is set correctly
        async with self.make_script():
            sleep_for = 5

            await self.configure_script(sleep_for=sleep_for)

            self.assertEqual(self.script.sleep_for, sleep_for)

    async def test_run(self):
        """
        Test that the script sleeps for the correct amount of time.
        """
        async with self.make_script():
            sleep_for = 5
            await self.configure_script(sleep_for=sleep_for)

            # Run the script
            await self.run_script()

    async def test_executable(self):
        scripts_dir = get_scripts_dir()
        script_path = scripts_dir / "sleep.py"
        await self.check_executable(script_path)


if __name__ == "__main__":
    unittest.main()
