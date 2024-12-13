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
import random
import types
import unittest

from lsst.ts import standardscripts
from lsst.ts.idl.enums.MTM1M3 import HardpointTest
from lsst.ts.maintel.standardscripts.m1m3 import CheckHardpoint
from lsst.ts.observatory.control.maintel.mtcs import MTCS, MTCSUsages

random.seed(47)  # for set_random_lsst_dds_partition_prefix


class TestCheckHardpoint(
    standardscripts.BaseScriptTestCase, unittest.IsolatedAsyncioTestCase
):
    async def basic_make_script(self, index):
        self.script = CheckHardpoint(index=index, add_remotes=False)

        self.script.mtcs = MTCS(
            self.script.domain, intended_usage=MTCSUsages.DryTest, log=self.script.log
        )

        self.script.mtcs.run_m1m3_hard_point_test = unittest.mock.AsyncMock(
            side_effect=self.mock_test_hardpoint
        )
        self.script.mtcs.enter_m1m3_engineering_mode = unittest.mock.AsyncMock()
        self.script.mtcs.exit_m1m3_engineering_mode = unittest.mock.AsyncMock()
        self.script.mtcs.assert_liveliness = unittest.mock.AsyncMock()
        self.script.mtcs.assert_all_enabled = unittest.mock.AsyncMock()
        self.script.mtcs.assert_m1m3_detailed_state = unittest.mock.AsyncMock()

        self.hardpoint_test_status = types.SimpleNamespace(
            testState=[HardpointTest.NOTTESTED] * 6
        )

        return (self.script,)

    async def mock_test_hardpoint(self, hp):
        await asyncio.sleep(5.0)
        self.hardpoint_test_status.testState[hp - 1] = HardpointTest.PASSED

    async def test_configure(self):
        # Try configure with "all" for hardpoints
        async with self.make_script():
            hardpoints = "all"

            await self.configure_script(
                hardpoints=hardpoints,
            )

            assert self.script.hardpoints == range(1, 7)
            assert self.script.program is None
            assert self.script.reason is None
            assert self.script.checkpoint_message is None

    async def test_configure_with_hardpoints(self):
        # Try configure with a vector of hardpoints for hardpoints
        async with self.make_script():
            hardpoints = [1, 2, 5]

            await self.configure_script(
                hardpoints=hardpoints,
            )

            assert self.script.hardpoints == hardpoints
            assert self.script.program is None
            assert self.script.reason is None
            assert self.script.checkpoint_message is None

    @unittest.mock.patch(
        "lsst.ts.standardscripts.BaseBlockScript.obs_id", "202306060001"
    )
    async def test_configure_with_program_reason(self):
        """Testing a valid configuration: with program and reason"""

        # Try configure with a list of valid actuators ids
        async with self.make_script():
            self.script.get_obs_id = unittest.mock.AsyncMock(
                side_effect=["202306060001"]
            )
            await self.configure_script(
                program="BLOCK-123",
                reason="SITCOM-321",
            )

            assert self.script.program == "BLOCK-123"
            assert self.script.reason == "SITCOM-321"
            assert (
                self.script.checkpoint_message
                == "CheckHardpoint BLOCK-123 202306060001 SITCOM-321"
            )

    async def test_run(self):
        # Start the test itself
        async with self.make_script():
            await self.configure_script()

            # Run the script
            await self.run_script()

            assert all(
                [
                    self.hardpoint_test_status.testState[i - 1] == HardpointTest.PASSED
                    for i in self.script.hardpoints
                ]
            )

    async def test_executable(self):
        scripts_dir = standardscripts.get_scripts_dir()
        script_path = scripts_dir / "maintel" / "m1m3" / "check_hardpoint.py"
        await self.check_executable(script_path)


if __name__ == "__main__":
    unittest.main()
