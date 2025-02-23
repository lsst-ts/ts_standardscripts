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
from unittest.mock import AsyncMock, MagicMock

import pytest
from lsst.ts import salobj, standardscripts
from lsst.ts.standardscripts.auxtel.atvent_start import ATVentStart
from lsst.ts.xml.enums.ATBuilding import FanDriveState, VentGateState
from lsst.ts.xml.enums.Script import ScriptState


class TestATVentStart(
    standardscripts.BaseScriptTestCase, unittest.IsolatedAsyncioTestCase
):
    async def basic_make_script(self, index):
        self.script = ATVentStart(index=index)
        return [
            self.script,
        ]

    async def test_executable(self):
        """Check the executable."""
        scripts_dir = standardscripts.get_scripts_dir()
        script_path = scripts_dir / "auxtel" / "atvent_start.py"
        await self.check_executable(script_path)

    async def test_configure(self):
        """Test valid and invalid configurations."""
        configs_good = (
            ("all defaults", dict(), [0, 1, 2, 3], None),
            ("frequency only", {"fan_frequency": 1.0}, [0, 1, 2, 3], 1.0),
            (
                "gates and frequency",
                {"gates_to_open": 0, "fan_frequency": 1.0},
                [0, -1, -1, -1],
                1.0,
            ),
            ("integer gate", {"gates_to_open": 0}, [0, -1, -1, -1], None),
            ("array gates zero", {"gates_to_open": []}, None, None),
            ("array gates one", {"gates_to_open": [0]}, [0, -1, -1, -1], None),
            ("array gates four", {"gates_to_open": [0, 0, 0, 0]}, [0, 0, 0, 0], None),
        )
        for (
            subtest_name,
            config,
            expected_gates_to_open,
            expected_fan_frequency,
        ) in configs_good:
            with self.subTest(subtest_name=subtest_name):
                async with self.make_script():
                    await self.configure_script(**config)
                    self.assertEqual(self.script.gates_to_open, expected_gates_to_open)
                    self.assertAlmostEqual(
                        self.script.fan_frequency, expected_fan_frequency
                    )

        configs_bad = (
            ("invalid value", {"asdf": 123, "gates_to_open": 2}),
            ("invalid gates", {"gates_to_open": "foo"}),
            ("too many gates", {"gates_to_open": [1, 1, 1, 1, 1]}),
            ("integer gate out of range", {"gates_to_open": 4}),
            ("integer negative gate", {"gates_to_open": -1}),
            ("array gate out of range", {"gates_to_open": [4]}),
            ("array negative gate", {"gates_to_open": [-1]}),
            ("invalid frequency", {"fan_frequency": "foo"}),
            ("negative frequency", {"fan_frequency": -1.0}),
        )
        for subtest_name, config in configs_bad:
            with self.subTest(subtest_name=subtest_name):
                async with self.make_script():
                    with pytest.raises(salobj.ExpectedError):
                        await self.configure_script(**config)

    async def run_with(
        self,
        config=dict(),
        summary_state=salobj.State.ENABLED,
        vent_gate_state=[2, 2, 3, 2],
        maximum_frequency=50.0,
        fan_frequency=20.0,
        fan_drive_state=FanDriveState.OPERATING,
        expected_final_state=ScriptState.DONE,
    ):
        async with self.make_script():
            # Mock the Remote object
            self.script.atbuilding_remote = MagicMock(spec=salobj.Remote)

            # Mock async methods (awaitable properties)
            self.script.atbuilding_remote.evt_summaryState = MagicMock()
            self.script.atbuilding_remote.evt_summaryState.aget = AsyncMock(
                return_value=MagicMock(summaryState=summary_state.value)
            )

            self.script.atbuilding_remote.cmd_openVentGate = MagicMock()
            self.script.atbuilding_remote.cmd_closeVentGate = MagicMock()
            self.script.atbuilding_remote.cmd_openVentGate.set_start = AsyncMock()
            self.script.atbuilding_remote.cmd_closeVentGate.set_start = AsyncMock()

            self.script.atbuilding_remote.evt_ventGateState = MagicMock()
            self.script.atbuilding_remote.evt_ventGateState.aget = AsyncMock(
                return_value=MagicMock(state=vent_gate_state)
            )

            self.script.atbuilding_remote.evt_maximumDriveFrequency = MagicMock()
            self.script.atbuilding_remote.evt_maximumDriveFrequency.aget = AsyncMock(
                return_value=MagicMock(driveFrequency=maximum_frequency)
            )

            self.script.atbuilding_remote.cmd_setExtractionFanManualControlMode = (
                MagicMock()
            )
            self.script.atbuilding_remote.cmd_setExtractionFanManualControlMode.set_start = (
                AsyncMock()
            )
            self.script.atbuilding_remote.cmd_startExtractionFan = MagicMock()
            self.script.atbuilding_remote.cmd_startExtractionFan.set_start = AsyncMock()
            self.script.atbuilding_remote.cmd_setExtractionFanDriveFreq = MagicMock()
            self.script.atbuilding_remote.cmd_setExtractionFanDriveFreq.set_start = (
                AsyncMock()
            )

            self.script.atbuilding_remote.evt_extractionFanDriveState = MagicMock()
            self.script.atbuilding_remote.evt_extractionFanDriveState.aget = AsyncMock(
                return_value=MagicMock(state=fan_drive_state.value)
            )

            self.script.atbuilding_remote.tel_extractionFan = MagicMock()
            self.script.atbuilding_remote.tel_extractionFan.aget = AsyncMock(
                return_value=MagicMock(driveFrequency=fan_frequency)
            )

            await self.configure_script(**config)
            await self.run_script(expected_final_state=expected_final_state)

    async def test_run_success(self):
        """The happy case where everything runs as expected."""
        await self.run_with({"fan_frequency": 20.0, "gates_to_open": 2})

        self.script.atbuilding_remote.cmd_openVentGate.set_start.assert_called_once()
        self.script.atbuilding_remote.cmd_closeVentGate.set_start.assert_called_once()
        self.script.atbuilding_remote.evt_ventGateState.aget.assert_called_once()

        self.script.atbuilding_remote.evt_maximumDriveFrequency.aget.assert_called_once()
        cmd_setExtractionFanManualControlMode = (
            self.script.atbuilding_remote.cmd_setExtractionFanManualControlMode
        )
        cmd_setExtractionFanManualControlMode.set_start.assert_called_once_with(
            enableManualControlMode=False
        )
        self.script.atbuilding_remote.cmd_startExtractionFan.set_start.assert_called_once()
        self.script.atbuilding_remote.cmd_setExtractionFanDriveFreq.set_start.assert_called_once_with(
            targetFrequency=20.0
        )
        self.script.atbuilding_remote.evt_extractionFanDriveState.aget.assert_called_once()
        self.script.atbuilding_remote.tel_extractionFan.aget.assert_called_once()

    async def test_run_without_gates(self):
        """Test that the gates are not operated if none are specified."""
        await self.run_with({"fan_frequency": 20.0, "gates_to_open": []})

        self.script.atbuilding_remote.cmd_openVentGate.set_start.assert_not_called()
        self.script.atbuilding_remote.cmd_closeVentGate.set_start.assert_not_called()

    async def test_run_without_fan(self):
        """Test that fan is not operated if a frequency is not specified."""
        await self.run_with({"gates_to_open": 2})

        self.script.atbuilding_remote.cmd_setExtractionFanManualControlMode.set_start.assert_not_called()
        self.script.atbuilding_remote.cmd_startExtractionFan.set_start.assert_not_called()
        self.script.atbuilding_remote.cmd_setExtractionFanDriveFreq.set_start.assert_not_called()

    async def test_csc_not_enabled(self):
        """Test that an error is returned if run with the CSC not enabled."""
        await self.run_with(
            {},
            summary_state=salobj.State.STANDBY,
            expected_final_state=ScriptState.FAILED,
        )
        self.assertRegex(self.script.state.reason, r"ATBuilding CSC must be ENABLED\.")

    async def test_gate_not_open(self):
        """Test for an error if the gates should have opened do not open."""
        await self.run_with(
            {},
            vent_gate_state=[VentGateState.CLOSED.value] * 4,
            expected_final_state=ScriptState.FAILED,
        )
        self.assertRegex(self.script.state.reason, r"Gate 0 did not open as expected\.")

    async def test_gate_not_closed(self):
        """Test for an error if the gates should have closed do not close."""
        await self.run_with(
            {"gates_to_open": [1]},
            vent_gate_state=[VentGateState.OPENED.value] * 4,
            expected_final_state=ScriptState.FAILED,
        )
        self.assertRegex(
            self.script.state.reason, r"Gate 0 did not close as expected\."
        )

    async def test_frequency_out_of_range(self):
        """Test for an error if the requested frequency is too high."""
        await self.run_with(
            {"fan_frequency": 1000000.0},
            expected_final_state=ScriptState.FAILED,
        )
        self.assertRegex(
            self.script.state.reason, r"Requested frequency .* exceeds maximum of"
        )

    async def test_incorrect_frequency(self):
        """Test for an error if the drive does not reach the frequency."""
        await self.run_with(
            {"fan_frequency": 10.0},
            expected_final_state=ScriptState.FAILED,
        )
        self.assertRegex(
            self.script.state.reason,
            r"Drive frequency .* does not match requested value",
        )
