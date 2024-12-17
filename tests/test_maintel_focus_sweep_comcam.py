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
# along with this program. If not, see <https://www.gnu.org/licenses/>.

import unittest
import unittest.mock as mock

import pytest
from lsst.ts import salobj, standardscripts
from lsst.ts.maintel.standardscripts import get_scripts_dir
from lsst.ts.maintel.standardscripts.focus_sweep_comcam import FocusSweepComCam


class TestFocusSweepComCam(
    standardscripts.BaseScriptTestCase, unittest.IsolatedAsyncioTestCase
):
    async def basic_make_script(self, index):
        self.script = FocusSweepComCam(index=index)

        self.mock_mtcs()
        self.mock_camera()
        self.mock_ocps()

        return (self.script,)

    def mock_mtcs(self):
        """Mock MTCS instances and its methods."""
        self.script.mtcs = mock.AsyncMock()
        self.script.mtcs.assert_liveliness = mock.AsyncMock()
        self.script.mtcs.assert_all_enabled = mock.AsyncMock()
        self.script.mtcs.offset_camera_hexapod = mock.AsyncMock()
        self.script.mtcs.offset_m2_hexapod = mock.AsyncMock()

    def mock_camera(self):
        """Mock camera instance and its methods."""
        self.script.comcam = mock.AsyncMock()
        self.script.comcam.assert_liveliness = mock.AsyncMock()
        self.script.comcam.assert_all_enabled = mock.AsyncMock()
        self.script.comcam.take_focus = mock.AsyncMock(return_value=[1234])

    def mock_ocps(self):
        """Mock OCPS instance and its methods."""
        self.script.ocps = mock.Mock()
        self.script.ocps.cmd_execute = mock.Mock()
        self.script.ocps.cmd_execute.set_start = mock.AsyncMock()

    async def test_configure(self):
        config = {
            "axis": "z",
            "focus_window": 1000,
            "n_steps": 11,
            "exp_time": 15.0,
            "filter": "g",
            "n_images_per_step": 1,
            "hexapod": "Camera",
        }

        async with self.make_script():
            await self.configure_script(**config)

            assert self.script.config.axis == "z"
            assert self.script.config.focus_window == 1000
            assert self.script.config.n_steps == 11
            assert self.script.config.exp_time == 15.0
            assert self.script.config.filter == "g"
            assert self.script.config.n_images_per_step == 1
            assert self.script.hexapod == "Camera"

    async def test_configure_focus_step_sequence(self):
        config = {
            "axis": "z",
            "focus_step_sequence": [-200, -100, 0, 100, 200],
            "exp_time": 15.0,
            "filter": "g",
            "n_images_per_step": 1,
            "hexapod": "Camera",
        }

        expected_step_sequence = [-200, -100, 0, 100, 200]
        async with self.make_script():
            await self.configure_script(**config)

            assert self.script.config.axis == "z"
            assert self.script.config.focus_window == 400
            assert self.script.config.n_steps == 5
            assert self.script.config.focus_step_sequence == expected_step_sequence
            assert self.script.config.exp_time == 15.0
            assert self.script.config.filter == "g"
            assert self.script.config.n_images_per_step == 1
            assert self.script.hexapod == "Camera"

    async def test_configure_focus_step_sequence_with_window(self):
        config = {
            "axis": "z",
            "focus_window": 400,
            "n_steps": 5,
            "exp_time": 15.0,
            "filter": "g",
            "n_images_per_step": 1,
            "hexapod": "Camera",
        }

        expected_step_sequence = [-200, -100, 0, 100, 200]
        async with self.make_script():
            await self.configure_script(**config)

            assert self.script.config.axis == "z"
            assert self.script.config.focus_window == 400
            assert self.script.config.n_steps == 5
            assert self.script.config.focus_step_sequence == expected_step_sequence
            assert self.script.config.exp_time == 15.0
            assert self.script.config.filter == "g"
            assert self.script.config.n_images_per_step == 1
            assert self.script.hexapod == "Camera"

    async def test_configure_ignore(self):
        config = {
            "axis": "z",
            "focus_window": 1000,
            "n_steps": 11,
            "exp_time": 15.0,
            "filter": "g",
            "n_images_per_step": 1,
            "hexapod": "Camera",
            "ignore": ["mtm1m3", "mtrotator"],
        }

        async with self.make_script():
            # Mock the components_attr to contain the ignored components
            self.script.mtcs.components_attr = ["mtm1m3", "mtrotator"]
            self.script.camera.components_attr = []

            await self.configure_script(**config)

            assert self.script.config.axis == "z"
            assert self.script.config.focus_window == 1000
            assert self.script.config.n_steps == 11
            assert self.script.config.exp_time == 15.0
            assert self.script.config.filter == "g"
            assert self.script.config.n_images_per_step == 1
            assert self.script.hexapod == "Camera"

            # Verify that the ignored components are correctly set to False
            assert not self.script.mtcs.check.mtm1m3
            assert not self.script.mtcs.check.mtrotator

    async def test_invalid_configuration(self):
        bad_configs = [
            {
                "axis": "invalid_axis",
                "focus_window": 1000,
                "n_steps": 100,
                "exp_time": 15.0,
                "filter": "g",
                "n_images_per_step": 1,
                "hexapod": "Camera",
            },
            {
                "axis": "z",
                "focus_window": 1000,
                "n_steps": 1,
                "exp_time": 15.0,
                "filter": "g",
                "n_images_per_step": 1,
                "hexapod": "Camera",
            },
        ]

        async with self.make_script():
            for bad_config in bad_configs:
                with pytest.raises(salobj.ExpectedError):
                    await self.configure_script(**bad_config)

    async def test_invalid_configuration_steps_and_window(self):
        bad_config = {
            "axis": "z",
            "focus_window": 400,
            "n_steps": 5,
            "focus_step_sequence": [-200, -100, 0, 100, 200],
            "exp_time": 15,
            "filter": "g",
            "n_images_per_step": 1,
            "hexapod": "Camera",
        }

        async with self.make_script():
            with pytest.raises(salobj.ExpectedError):
                await self.configure_script(**bad_config)

    async def test_focus_sweep(self):
        config = {
            "axis": "z",
            "focus_window": 1000,
            "n_steps": 11,
            "exp_time": 15.0,
            "filter": "g",
            "n_images_per_step": 1,
            "hexapod": "Camera",
        }

        async with self.make_script():
            await self.configure_script(**config)
            await self.run_script()

            # Check if the hexapod moved the expected number of times
            assert (
                self.script.mtcs.offset_camera_hexapod.call_count
                == config["n_steps"] + 1
            )

            # Assert the offset_m2_hexapod was not called
            self.script.mtcs.offset_m2_hexapod.assert_not_called()

            # Check if the camera took the expected number of images
            assert self.script.comcam.take_focus.call_count == config["n_steps"]

            # Check if the OCPS command was called
            self.script.ocps.cmd_execute.set_start.assert_called_once()

    async def test_focus_sweep_sim_mode(self):
        config = {
            "axis": "z",
            "focus_window": 1000,
            "n_steps": 3,
            "exp_time": 15.0,
            "filter": "g",
            "n_images_per_step": 1,
            "hexapod": "M2",
            "sim": True,
        }

        async with self.make_script():
            await self.configure_script(**config)
            await self.run_script()

            # Check if the hexapod moved the expected number of times
            assert (
                self.script.mtcs.offset_m2_hexapod.call_count == config["n_steps"] + 1
            )

            # Asert that the offset_camera_hexapod was not called
            self.script.mtcs.offset_camera_hexapod.assert_not_called()

            # Check if the camera took the expected number of images
            assert self.script.comcam.take_focus.call_count == config["n_steps"]

            # Check if the OCPS command was called
            self.script.ocps.cmd_execute.set_start.assert_called_once()

            # Verify that simulation mode is set correctly
            assert self.script.comcam.simulation_mode

    async def test_cleanup(self):
        config = {
            "axis": "z",
            "focus_window": 1000,
            "n_steps": 11,
            "exp_time": 15.0,
            "filter": "g",
            "n_images_per_step": 1,
            "hexapod": "Camera",
        }

        async with self.make_script():
            await self.configure_script(**config)

            # Simulate an error during the focus sweep to trigger cleanup
            self.script.iterations_started = True
            self.script.total_focus_offset = 1000  # Simulate some offset
            with mock.patch.object(
                self.script, "focus_sweep", side_effect=Exception("Test exception")
            ):
                with pytest.raises(Exception):
                    await self.script.run_block()

            await self.script.cleanup()

            # Ensure the hexapod is returned to the original position
            self.script.mtcs.offset_camera_hexapod.assert_any_call(
                x=0, y=0, z=-self.script.total_focus_offset, u=0, v=0, w=0
            )

    async def test_executable(self):
        scripts_dir = get_scripts_dir()
        script_path = scripts_dir / "focus_sweep_comcam.py"
        await self.check_executable(script_path)
