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
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

import unittest

from lsst.ts import standardscripts
from lsst.ts.standardscripts.maintel import HomeBothAxes


class TestHomeBothAxes(
    standardscripts.BaseScriptTestCase, unittest.IsolatedAsyncioTestCase
):
    async def basic_make_script(self, index):
        self.script = HomeBothAxes(index=index, add_remotes=False)

        self.script.mtcs.rem.mtmount = unittest.mock.AsyncMock()

        return (self.script,)

    async def test_run(self):
        async with self.make_script():
            await self.configure_script()

            await self.run_script()

            self.script.mtcs.rem.mtmount.cmd_homeBothAxes.start.assert_awaited_once_with(
                timeout=self.script.home_both_axes_timeout
            )

    async def test_executable(self):
        scripts_dir = standardscripts.get_scripts_dir()
        script_path = scripts_dir / "maintel" / "home_both_axes.py"
        print(script_path)
        await self.check_executable(script_path)


if __name__ == "__main__":
    unittest.main()
