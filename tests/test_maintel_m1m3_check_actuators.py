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
import logging
import types
import unittest
import warnings

from lsst.ts import salobj
from lsst.ts.maintel.standardscripts.m1m3 import CheckActuators
from lsst.ts.observatory.control.maintel.mtcs import MTCS, MTCSUsages
from lsst.ts.standardscripts import BaseScriptTestCase, get_scripts_dir
from lsst.ts.xml.enums.MTM1M3 import BumpTest

try:
    from lsst.ts.idl.enums.MTM1M3 import DetailedState
except ImportError:
    warnings.warn(
        "Could not import MTM1M3 from lsst.ts.idl; importing from lsst.ts.xml",
        UserWarning,
    )
    from lsst.ts.xml.enums.MTM1M3 import DetailedStates as DetailedState


class TestCheckActuators(BaseScriptTestCase, unittest.IsolatedAsyncioTestCase):
    @classmethod
    def setUpClass(cls):
        cls.log = logging.getLogger(cls.__name__)

    async def basic_make_script(self, index):
        self.script = CheckActuators(index=index)

        self.script.mtcs = MTCS(
            self.script.domain, intended_usage=MTCSUsages.DryTest, log=self.script.log
        )
        await self.script.configure_tcs()
        self.script.mtcs.run_m1m3_actuator_bump_test = unittest.mock.AsyncMock(
            side_effect=self.mock_test_bump
        )
        self.script.mtcs.stop_m1m3_bump_test = unittest.mock.AsyncMock()
        self.script.mtcs.enter_m1m3_engineering_mode = unittest.mock.AsyncMock()
        self.script.mtcs.exit_m1m3_engineering_mode = unittest.mock.AsyncMock()
        self.script.mtcs.assert_liveliness = unittest.mock.AsyncMock()
        self.script.mtcs.assert_all_enabled = unittest.mock.AsyncMock()
        self.script.mtcs.assert_m1m3_detailed_state = unittest.mock.AsyncMock()

        self.script.mtcs.get_m1m3_bump_test_status = unittest.mock.AsyncMock(
            side_effect=self.mock_get_m1m3_bump_test_status
        )

        self.script.mtcs.rem.mtm1m3 = unittest.mock.AsyncMock()
        self.script.mtcs.rem.mtm1m3.configure_mock(
            **{
                "evt_detailedState.aget": self.get_m1m3_detailed_state,
            }
        )

        self.bump_test_status = types.SimpleNamespace(
            testState=[BumpTest.NOTTESTED] * len(self.script.m1m3_actuator_ids)
        )

        self.failed_primary_test = set()
        self.failed_secondary_test = set()

        return (self.script,)

    async def get_m1m3_detailed_state(self, *args, **kwags):
        return types.SimpleNamespace(detailedState=DetailedState.PARKED)

    # Side effects
    async def mock_test_bump(self, actuator_id, primary, secondary):
        await asyncio.sleep(0.5)
        actuator_index = self.script.mtcs.get_m1m3_actuator_index(actuator_id)
        self.bump_test_status.testState[actuator_index] = (
            BumpTest.PASSED
            if actuator_id not in self.failed_primary_test
            and actuator_id not in self.failed_secondary_test
            else BumpTest.FAILED
        )
        self.log.info(f"{self.bump_test_status.testState[actuator_index]!r}")
        if self.bump_test_status.testState[actuator_index] == BumpTest.FAILED:
            raise RuntimeError(f"Actuator {actuator_id} bump test failed.")

    # Create a side effect function for mock_bump_test_status method from mcts
    # object. This function will be called when mock_bump_test_status method is
    # called
    async def mock_get_m1m3_bump_test_status(self, actuator_id):
        primary_test_status = (
            BumpTest.PASSED
            if actuator_id not in self.failed_primary_test
            else BumpTest.FAILED
        )
        secondary_test_status = (
            None
            if actuator_id not in self.script.mtcs.get_m1m3_actuator_secondary_ids()
            else (
                BumpTest.PASSED
                if actuator_id not in self.failed_secondary_test
                else BumpTest.FAILED
            )
        )

        return (primary_test_status, secondary_test_status)

    async def test_configure_all(self):
        """Testing a valid configuration: all actuators"""

        # Configure with "all" actuators
        async with self.make_script():
            actuators = "all"

            await self.configure_script(actuators=actuators)

            assert self.script.actuators_to_test == self.script.m1m3_actuator_ids
            assert self.script.program is None
            assert self.script.reason is None
            assert self.script.checkpoint_message is None

    async def test_configure_last_failed(self):
        """Testing a valid configuration: last failed actuators"""

        # Configure with "last_failed" actuators
        async with self.make_script():
            actuators = "last_failed"

            await self.configure_script(actuators=actuators)

            # At configuration stage all actuators are selected
            # for later filtering
            assert self.script.actuators_to_test == self.script.m1m3_actuator_ids
            assert self.script.program is None
            assert self.script.reason is None
            assert self.script.checkpoint_message is None

    async def test_configure_valid_ids(self):
        """Testing a valid configuration: valid actuators ids"""

        # Try configure with a list of valid actuators ids
        async with self.make_script():
            actuators = [101, 210, 301, 410]

            await self.configure_script(
                actuators=actuators,
            )

            assert self.script.actuators_to_test == actuators
            assert self.script.program is None
            assert self.script.reason is None
            assert self.script.checkpoint_message is None

    async def test_configure_bad(self):
        """Testing an invalid configuration: bad actuators ids"""

        async with self.make_script():
            # Invalid actuators: 501 and 505
            actuators = [501, 505]

            # If actuators_bad_ids is not empty, it should raise a ValueError
            actuators_bad_ids = [
                actuator
                for actuator in actuators
                if actuator not in self.script.m1m3_actuator_ids
            ]
            if actuators_bad_ids:
                with self.assertRaises(salobj.ExpectedError):
                    await self.configure_script(
                        actuators=actuators_bad_ids,
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

    async def test_run(self):
        # Run the script
        async with self.make_script():
            actuators = "all"
            await self.configure_script(actuators=actuators)

            # Run the script
            await self.run_script()

            # Assert all passed on mocked bump test. Had to get indexes.
            actuators_to_test_index = [
                self.script.mtcs.get_m1m3_actuator_index(actuator_id)
                for actuator_id in self.script.actuators_to_test
            ]

            assert all(
                [
                    self.bump_test_status.testState[actuator_index] == BumpTest.PASSED
                    for actuator_index in actuators_to_test_index
                ]
            )
            # Expected awaint for assert_all_enabled method
            expected_awaits = len(self.script.actuators_to_test) + 1

            # Assert we await once for all mock methods defined above
            self.script.mtcs.enter_m1m3_engineering_mode.assert_awaited_once()
            self.script.mtcs.exit_m1m3_engineering_mode.assert_awaited_once()
            self.script.mtcs.assert_liveliness.assert_awaited_once()
            self.script.mtcs.assert_m1m3_detailed_state.assert_awaited_once()
            assert self.script.mtcs.assert_all_enabled.await_count == expected_awaits

            expected_calls = [
                unittest.mock.call(
                    actuator_id=actuator_id,
                    primary=True,
                    secondary=self.script.has_secondary_actuator(actuator_id),
                )
                for actuator_id in self.script.m1m3_actuator_ids
            ]

            self.script.mtcs.run_m1m3_actuator_bump_test.assert_has_calls(
                expected_calls
            )

    async def test_run_with_failed_actuators(self):
        # Run the script
        async with self.make_script():
            actuators = "all"
            await self.configure_script(actuators=actuators)
            self.failed_primary_test = {101, 220, 218}
            self.failed_secondary_test = {220, 330}
            # Run the script
            with self.assertRaises(AssertionError, msg="FAILED the bump test"):
                await self.run_script()

            # Assert all passed on mocked bump test. Had to get indexes.
            actuators_to_test_index = [
                self.script.mtcs.get_m1m3_actuator_index(actuator_id)
                for actuator_id in self.script.actuators_to_test
                if actuator_id not in self.failed_primary_test
                and actuator_id not in self.failed_secondary_test
            ]

            assert all(
                [
                    self.bump_test_status.testState[actuator_index] == BumpTest.PASSED
                    for actuator_index in actuators_to_test_index
                ]
            )
            # Expected awaint for assert_all_enabled method
            expected_awaits = len(self.script.actuators_to_test) + 1

            # Assert we await once for all mock methods defined above
            self.script.mtcs.enter_m1m3_engineering_mode.assert_awaited_once()
            self.script.mtcs.exit_m1m3_engineering_mode.assert_awaited_once()
            self.script.mtcs.assert_liveliness.assert_awaited_once()
            self.script.mtcs.assert_m1m3_detailed_state.assert_awaited_once()
            assert self.script.mtcs.assert_all_enabled.await_count == expected_awaits

            expected_calls = [
                unittest.mock.call(
                    actuator_id=actuator_id,
                    primary=True,
                    secondary=self.script.has_secondary_actuator(actuator_id),
                )
                for actuator_id in self.script.m1m3_actuator_ids
            ]

            self.script.mtcs.run_m1m3_actuator_bump_test.assert_has_calls(
                expected_calls
            )

    async def test_run_last_failed_actuators(self):
        # Run the script
        async with self.make_script():
            await self.configure_script(actuators="last_failed")
            # Sets up the actuators that will report a failed last bump test
            self.failed_primary_test = {101, 220, 218}
            self.failed_secondary_test = {220, 330}
            # Actuators that must be tested by the script
            expected_to_test = self.failed_primary_test | self.failed_secondary_test
            # Run the script
            # (assertion errors expected, as failed actuators will fail again)
            with self.assertRaises(AssertionError, msg="FAILED the bump test"):
                await self.run_script()

            # Expected awaint for assert_all_enabled method
            expected_awaits = len(self.script.actuators_to_test) + 1

            # Assert we await once for all mock methods defined above
            self.script.mtcs.enter_m1m3_engineering_mode.assert_awaited_once()
            self.script.mtcs.exit_m1m3_engineering_mode.assert_awaited_once()
            self.script.mtcs.assert_liveliness.assert_awaited_once()
            self.script.mtcs.assert_m1m3_detailed_state.assert_awaited_once()
            assert self.script.mtcs.assert_all_enabled.await_count == expected_awaits

            # Check that the last failed actuators were tested
            expected_calls = [
                unittest.mock.call(
                    actuator_id=actuator_id,
                    primary=True,
                    secondary=self.script.has_secondary_actuator(actuator_id),
                )
                for actuator_id in expected_to_test
            ]

            self.script.mtcs.run_m1m3_actuator_bump_test.assert_has_calls(
                expected_calls
            )

            # Check that no other actuators were tested
            not_expected_to_test_indexes = [
                self.script.mtcs.get_m1m3_actuator_index(actuator_id)
                for actuator_id in self.script.m1m3_actuator_ids
                if actuator_id not in expected_to_test
            ]

            assert all(
                self.bump_test_status.testState[actuator_index] == BumpTest.NOTTESTED
                for actuator_index in not_expected_to_test_indexes
            )

    async def test_executable(self):
        scripts_dir = get_scripts_dir()
        script_path = scripts_dir / "maintel" / "m1m3" / "check_actuators.py"
        await self.check_executable(script_path)


if __name__ == "__main__":
    unittest.main()
