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
import unittest

import numpy as np
from lsst.ts import salobj
from lsst.ts.maintel.standardscripts.m2 import CheckActuators
from lsst.ts.standardscripts import BaseScriptTestCase, get_scripts_dir

# TODO: DM-41592 move constants from lsst.ts.m2com to ts-xml
NUM_ACTUATOR = 78
NUM_TANGENT_LINK = 6


class TestCheckActuators(BaseScriptTestCase, unittest.IsolatedAsyncioTestCase):
    async def basic_make_script(self, index):
        self.script = CheckActuators(index=index)
        self.script.mtcs = unittest.mock.AsyncMock()
        self.script.mtcs.components_attr = ["mtm2"]
        self.script.mtcs.run_m2_actuator_bump_test = unittest.mock.AsyncMock(
            side_effect=self.mock_test_bump
        )
        self.script.mtcs.stop_m2_bump_test = unittest.mock.AsyncMock()
        self.script.mtcs.assert_liveliness = unittest.mock.AsyncMock()
        self.script.mtcs.assert_all_enabled = unittest.mock.AsyncMock()
        self.script.mtcs.get_m2_hardpoints = unittest.mock.AsyncMock(
            side_effect=self.mock_get_m2_hardpoints
        )
        self.script.mtcs.run_m2_actuator_bump_test_with_error = unittest.mock.AsyncMock(
            side_effect=self.mock_test_bump_with_error
        )
        self.hardpoint_ids = list([6, 16, 26, 74, 76, 78])
        num_axial_actuator = NUM_ACTUATOR - NUM_TANGENT_LINK
        self.axial_actuator_ids = list(
            [
                actuator
                for actuator in np.arange(num_axial_actuator)
                if actuator + 1 not in self.hardpoint_ids
            ]
        )
        self.script.mtcs.rem.mtm2 = unittest.mock.AsyncMock()

        return (self.script,)

    # Side effects
    async def mock_test_bump(self, actuator, period, force):
        await asyncio.sleep(0.5)

    async def mock_test_bump_with_error(self, actuator, period, force):
        if actuator == 10:
            raise salobj.base.AckError("Testing command Error", None)
        await asyncio.sleep(0.5)

    # Create a side effect function for mock_bump_test_status method from mcts
    # object. This function will be called when mock_bump_test_status method is
    # called
    async def mock_get_m2_hardpoints(self):
        return self.hardpoint_ids

    async def test_configure_all(self):
        """Testing a valid configuration: all actuators"""

        # Configure with "all" actuators
        async with self.make_script():
            actuators = "all"

            await self.configure_script(actuators=actuators)
            assert self.script.actuators_to_test == self.axial_actuator_ids
            assert self.script.program is None
            assert self.script.reason is None
            assert self.script.checkpoint_message is None

    async def test_configure_valid_ids(self):
        """Testing a valid configuration: valid actuators ids"""

        # Try configure with a list of valid actuators ids
        async with self.make_script():
            actuators = [7, 8, 9, 10]

            await self.configure_script(
                actuators=actuators,
            )

            assert self.script.actuators_to_test == actuators
            assert self.script.program is None
            assert self.script.reason is None
            assert self.script.checkpoint_message is None

    async def test_configure_bad_hardpoint(self):
        """Testing an invalid configuration: bad actuators ids"""

        async with self.make_script():
            # Invalid actuators: actuator is a hardpoint
            actuators = [5]

            with self.assertRaises(salobj.ExpectedError):
                await self.configure_script(
                    actuators=actuators,
                )

    async def test_configure_bad_invalid_id(self):
        """Testing an invalid configuration: bad actuators ids"""

        async with self.make_script():
            # Invalid actuators: value greater than max id
            actuators = [105]

            with self.assertRaises(salobj.ExpectedError):
                await self.configure_script(
                    actuators=actuators,
                )

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
                == "CheckActuators BLOCK-123 202306060001 SITCOM-321"
            )

    async def test_run_with_error(self):
        # Run the script
        async with self.make_script():
            run_m2_actuator_bump_test_side_effect = (
                self.script.mtcs.run_m2_actuator_bump_test.side_effect
            )
            self.script.mtcs.run_m2_actuator_bump_test.side_effect = (
                self.mock_test_bump_with_error
            )
            actuators = [7, 8, 9, 10, 11]
            await self.configure_script(actuators=actuators)

            # Run the script
            run_data = self.script.cmd_run.DataType()
            await self.script.do_run(run_data)
            await self.script.done_task

            assert self.script.failed_actuator_ids == list([10])
        self.script.mtcs.run_m2_actuator_bump_test.side_effect = (
            run_m2_actuator_bump_test_side_effect
        )

    async def test_run(self):
        # Run the script
        async with self.make_script():
            actuators = "all"
            await self.configure_script(actuators=actuators)

            # Run the script
            await self.run_script()

            # Expected awaint for assert_all_enabled method
            expected_awaits = len(self.script.actuators_to_test) + 1

            # Assert we await once for all mock methods defined above
            self.script.mtcs.assert_liveliness.assert_awaited_once()
            assert self.script.mtcs.assert_all_enabled.await_count == expected_awaits

            expected_calls = [
                unittest.mock.call(
                    actuator=actuator,
                    period=self.script.period,
                    force=self.script.force,
                )
                for actuator in self.axial_actuator_ids
            ]

            self.script.mtcs.run_m2_actuator_bump_test.assert_has_calls(expected_calls)

    async def test_executable(self):
        scripts_dir = get_scripts_dir()
        script_path = scripts_dir / "maintel" / "m2" / "check_actuators.py"
        await self.check_executable(script_path)


if __name__ == "__main__":
    unittest.main()
