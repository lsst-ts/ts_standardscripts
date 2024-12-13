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

import contextlib
import unittest

from lsst.ts import standardscripts, utils
from lsst.ts.maintel.standardscripts.m2.enable_closed_loop import EnableM2ClosedLoop


class TestEnableM2ClosedLoop(
    standardscripts.BaseScriptTestCase, unittest.IsolatedAsyncioTestCase
):
    async def basic_make_script(self, index):
        self.script = EnableM2ClosedLoop(index=index)
        self.script.mtcs = unittest.mock.AsyncMock()
        self.script.mtcs.start_task = utils.make_done_future()
        self.script.mtcs.enable_m2_balance_system = unittest.mock.AsyncMock()

        return (self.script,)

    @contextlib.asynccontextmanager
    async def make_dry_script(self):
        async with self.make_script():
            self.script.mtcs = unittest.mock.AsyncMock()
            self.script.mtcs.enable_m2_balance_system = unittest.mock.AsyncMock()
            yield

    @unittest.mock.patch(
        "lsst.ts.standardscripts.BaseBlockScript.obs_id", "202306060001"
    )
    async def test_configure_with_program_reason(self):
        async with self.make_dry_script():
            self.script.get_obs_id = unittest.mock.AsyncMock(
                side_effect=["202312190001"]
            )
            program = "BLOCK-123"
            reason = "SITCOM-321"
            await self.configure_script(
                program=program,
                reason=reason,
            )

            assert self.script.program == program
            assert self.script.reason == reason
            assert (
                self.script.checkpoint_message
                == "EnableM2ClosedLoop BLOCK-123 202312190001 SITCOM-321"
            )

    async def test_run(self):
        async with self.make_script():
            await self.configure_script()
            await self.run_script()

            self.script.mtcs.enable_m2_balance_system.assert_awaited_once()

            assert self.script.program is None
            assert self.script.reason is None
            assert self.script.checkpoint_message is None

    async def test_executable(self):
        scripts_dir = standardscripts.get_scripts_dir()
        script_path = scripts_dir / "maintel" / "m2" / "enable_closed_loop.py"
        print(script_path)
        await self.check_executable(script_path)


if __name__ == "__main__":
    unittest.main()
