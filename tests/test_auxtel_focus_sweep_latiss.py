# This file is part of ts_auxtel_standardscripts
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
from lsst.ts.auxtel.standardscripts import get_scripts_dir
from lsst.ts.auxtel.standardscripts.focus_sweep_latiss import FocusSweepLatiss


class TestFocusSweepLatiss(
    standardscripts.BaseScriptTestCase, unittest.IsolatedAsyncioTestCase
):
    async def basic_make_script(self, index):
        self.script = FocusSweepLatiss(index=index)

        self.mock_atcs()
        self.mock_camera()
        self.mock_ocps()

        return (self.script,)

    def mock_atcs(self):
        """Mock ATCS instances and its methods."""
        self.script.atcs = mock.AsyncMock()
        self.script.atcs.assert_liveliness = mock.AsyncMock()
        self.script.atcs.assert_all_enabled = mock.AsyncMock()
        self.script.atcs.offset_aos_lut = mock.AsyncMock()

    def mock_camera(self):
        """Mock camera instance and its methods."""
        self.script.latiss = mock.AsyncMock()
        self.script.latiss.assert_liveliness = mock.AsyncMock()
        self.script.latiss.assert_all_enabled = mock.AsyncMock()
        self.script.latiss.take_focus = mock.AsyncMock(return_value=[1234])

    def mock_ocps(self):
        """Mock OCPS instance and its methods."""
        self.script.ocps = mock.Mock()
        self.script.ocps.cmd_execute = mock.Mock()
        self.script.ocps.cmd_execute.set_start = mock.AsyncMock()

    async def test_configure(self):
        config = {
            "axis": "x",
            "focus_window": 700,  # Value measured in um
            "n_steps": 7,
            "exp_time": 10.0,
            "filter": "SDSSr_65mm",
            "grating": 1,
            "n_images_per_step": 1,
        }

        async with self.make_script():
            await self.configure_script(**config)

            assert self.script.config.axis == "x"
            self.assertAlmostEqual(
                self.script.config.focus_window, 0.7
            )  # Checks that translation to mm was made
            assert self.script.config.n_steps == 7
            assert self.script.config.exp_time == 10.0
            assert self.script.config.filter == "SDSSr_65mm"
            assert self.script.config.grating == 1
            assert self.script.config.n_images_per_step == 1

    async def test_configure_focus_step_sequence(self):
        config = {
            "axis": "x",
            "focus_step_sequence": [-200, -100, 0, 100, 200],  # Measured in um
            "exp_time": 10.0,
            "filter": "SDSSr_65mm",
            "grating": 1,
            "n_images_per_step": 1,
        }

        expected_step_sequence = [-0.2, -0.1, 0, 0.1, 0.2]  # Measured in mm
        async with self.make_script():
            await self.configure_script(**config)

            assert self.script.config.axis == "x"
            self.assertAlmostEqual(
                self.script.config.focus_window, 0.4
            )  # Measured in mm
            assert self.script.config.n_steps == 5
            for step, expected_step in zip(
                self.script.config.focus_step_sequence, expected_step_sequence
            ):
                self.assertAlmostEqual(step, expected_step)
            assert self.script.config.exp_time == 10.0
            assert self.script.config.filter == "SDSSr_65mm"
            assert self.script.config.grating == 1
            assert self.script.config.n_images_per_step == 1

    async def test_configure_focus_step_sequence_with_window(self):
        config = {
            "axis": "x",
            "focus_window": 400,  # Measured in um
            "n_steps": 5,
            "exp_time": 10.0,
            "filter": "SDSSr_65mm",
            "grating": 1,
            "n_images_per_step": 1,
        }

        expected_step_sequence = [-0.2, -0.1, 0, 0.1, 0.2]
        async with self.make_script():
            await self.configure_script(**config)

            assert self.script.config.axis == "x"
            self.assertAlmostEqual(
                self.script.config.focus_window, 0.4  # Measured in mm
            )
            assert self.script.config.n_steps == 5
            for step, expected_step in zip(
                self.script.config.focus_step_sequence, expected_step_sequence
            ):
                self.assertAlmostEqual(step, expected_step)
            assert self.script.config.exp_time == 10.0
            assert self.script.config.filter == "SDSSr_65mm"
            assert self.script.config.grating == 1
            assert self.script.config.n_images_per_step == 1

    async def test_configure_ignore(self):
        config = {
            "axis": "x",
            "focus_window": 700,  # Measured in um
            "n_steps": 7,
            "exp_time": 10.0,
            "filter": "SDSSr_65mm",
            "grating": "blue300lpmm_qn1",
            "n_images_per_step": 1,
            "ignore": ["atdome", "atdometrajectory"],
        }

        async with self.make_script():
            # Mock the components_attr to contain the ignored components
            self.script.atcs.components_attr = ["atdome", "atdometrajectory"]
            self.script.camera.components_attr = []

            await self.configure_script(**config)

            assert self.script.config.axis == "x"
            self.assertAlmostEqual(
                self.script.config.focus_window, 0.7  # Measured in mm
            )
            assert self.script.config.n_steps == 7
            assert self.script.config.exp_time == 10.0
            assert self.script.config.filter == "SDSSr_65mm"
            assert self.script.config.grating == "blue300lpmm_qn1"
            assert self.script.config.n_images_per_step == 1

            # Verify that the ignored components are correctly set to False
            assert not self.script.atcs.check.atdome
            assert not self.script.atcs.check.atdometrajectory

    async def test_invalid_configuration(self):
        bad_configs = [
            {
                "axis": "invalid_axis",
                "focus_window": 700,  # Measured in um
                "n_steps": 7,
                "exp_time": 10,
                "filter": "SDSSr_65mm",
                "grating": "blue300lpmm_qn1",
                "n_images_per_step": 1,
            },
            {
                "axis": "z",
                "focus_window": 700,  # Measured in um
                "n_steps": 1,
                "exp_time": 10.0,
                "filter": "SDSSr_65mm",
                "grating": "blue300lpmm_qn1",
                "n_images_per_step": 1,
            },
        ]

        async with self.make_script():
            for bad_config in bad_configs:
                with pytest.raises(salobj.ExpectedError):
                    await self.configure_script(**bad_config)

    async def test_invalid_configuration_steps_and_window(self):
        bad_config = {
            "axis": "x",
            "focus_window": 400,  # Measured in um
            "n_steps": 5,
            "focus_step_sequence": [-200, -100, 0, 100, 200],  # Measured in um
            "exp_time": 10,
            "filter": "SDSSr_65mm",
            "grating": "blue300lpmm_qn1",
            "n_images_per_step": 1,
        }

        async with self.make_script():
            with pytest.raises(salobj.ExpectedError):
                await self.configure_script(**bad_config)

    async def test_focus_sweep(self):
        config = {
            "axis": "x",
            "focus_window": 700,  # Measured in um
            "n_steps": 7,
            "exp_time": 10.0,
            "filter": "SDSSr_65mm",
            "grating": "blue300lpmm_qn1",
            "n_images_per_step": 1,
        }

        async with self.make_script():
            await self.configure_script(**config)
            await self.run_script()

            # Check if the hexapod moved the expected number of times
            assert self.script.atcs.offset_aos_lut.call_count == config["n_steps"] + 1

            # Check if the camera took the expected number of images
            assert self.script.latiss.take_focus.call_count == config["n_steps"]

            # Check if the OCPS command was called
            self.script.ocps.cmd_execute.set_start.assert_called_once()

    async def test_cleanup(self):
        config = {
            "axis": "x",
            "focus_window": 700,  # Measured in um
            "n_steps": 7,
            "exp_time": 10.0,
            "filter": "SDSSr_65mm",
            "grating": "blue300lpmm_qn1",
            "n_images_per_step": 1,
        }

        async with self.make_script():
            await self.configure_script(**config)

            # Simulate an error during the focus sweep to trigger cleanup
            self.script.iterations_started = True
            self.script.total_focus_offset = 400  # Simulate some offset
            with mock.patch.object(
                self.script, "focus_sweep", side_effect=Exception("Test exception")
            ):
                with pytest.raises(Exception):
                    await self.script.run_block()

            await self.script.cleanup()

            # Ensure the hexapod is returned to the original position
            self.script.atcs.offset_aos_lut.assert_any_call(
                x=-self.script.total_focus_offset, y=0, z=0, u=0, v=0
            )

    async def test_executable(self):
        scripts_dir = get_scripts_dir()
        script_path = scripts_dir / "focus_sweep_latiss.py"
        await self.check_executable(script_path)
