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
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

import unittest
from unittest.mock import patch

from lsst.ts import standardscripts
from lsst.ts.maintel.standardscripts import HomeBothAxes, get_scripts_dir
from lsst.ts.observatory.control.maintel.mtcs import MTCS, MTCSUsages


class TestHomeBothAxes(
    standardscripts.BaseScriptTestCase, unittest.IsolatedAsyncioTestCase
):
    async def basic_make_script(self, index):
        self.script = HomeBothAxes(index=index)

        self.script.mtcs = MTCS(
            domain=self.script.domain,
            intended_usage=MTCSUsages.DryTest,
            log=self.script.log,
        )
        self.script.mtcs.rem.mtmount = unittest.mock.AsyncMock()
        self.script.mtcs.lower_m1m3 = unittest.mock.AsyncMock()
        self.script.mtcs.disable_m1m3_balance_system = unittest.mock.AsyncMock()
        self.script.mtcs.enable_m1m3_balance_system = unittest.mock.AsyncMock()

        return (self.script,)

    async def test_run(self):
        async with self.make_script():
            await self.configure_script()

            await self.run_script()

            self.script.mtcs.disable_m1m3_balance_system.assert_not_called()
            self.script.mtcs.rem.mtmount.cmd_homeBothAxes.start.assert_awaited_once_with(
                timeout=self.script.home_both_axes_timeout
            )

    async def test_run_with_balance_disabled(self):
        async with self.make_script():
            await self.configure_script(disable_m1m3_force_balance=True)

            await self.run_script()

            self.script.mtcs.disable_m1m3_balance_system.assert_awaited_once()

            self.script.mtcs.rem.mtmount.cmd_homeBothAxes.start.assert_awaited_once_with(
                timeout=self.script.home_both_axes_timeout
            )

    async def test_deprecated_ignore_m1m3_usage(self):
        async with self.make_script():

            with patch.object(self.script.log, "warning") as mock_log_warning:
                await self.configure_script(ignore_m1m3=True)

                mock_log_warning.assert_called_once_with(
                    "The 'ignore_m1m3' configuration property is deprecated and will be removed"
                    " in future releases. Please use 'disable_m1m3_force_balance' instead.",
                    DeprecationWarning,
                    stacklevel=2,
                )

            await self.run_script()

            self.script.mtcs.disable_m1m3_balance_system.assert_not_called()

            self.script.mtcs.rem.mtmount.cmd_homeBothAxes.start.assert_awaited_once_with(
                timeout=self.script.home_both_axes_timeout
            )

    async def ttest_deprecated_ignore_m1m3_usage(self):
        async with self.make_script():

            with self.assertWarns(DeprecationWarning) as cm:
                await self.configure_script(ignore_m1m3=True)

            self.assertIn(
                "The 'ignore_m1m3' configuration property is deprecated and will be removed"
                " in future releases. Please use 'disable_m1m3_force_balance' instead.",
                str(cm.warning),
            )

            await self.run_script()

            # Assert that homeBothAxes command was called
            self.script.mtcs.rem.mtmount.cmd_homeBothAxes.start.assert_awaited_once_with(
                timeout=self.script.home_both_axes_timeout
            )

    async def test_executable(self):
        scripts_dir = get_scripts_dir()
        script_path = scripts_dir / "home_both_axes.py"
        print(script_path)
        await self.check_executable(script_path)


if __name__ == "__main__":
    unittest.main()
