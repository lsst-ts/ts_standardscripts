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

import logging
import os
import random
import types
import unittest
import warnings

from lsst.ts import salobj, standardscripts, utils
from lsst.ts.standardscripts.maintel.calibration import PowerOffTunableLaser
from lsst.ts.xml.enums.TunableLaser import LaserDetailedState

# TODO: (DM-46168) Revert workaround for TunableLaser XML changes
try:
    from lsst.ts.xml.enums.TunableLaser import (
        OpticalConfiguration as LaserOpticalConfiguration,
    )
except ImportError:
    warnings.warn(
        "OpticalConfiguration enumeration not availble in ts-xml. Using local version."
    )
    from lsst.ts.observatory.control.utils.enums import LaserOpticalConfiguration

random.seed(47)  # for set_random_lsst_dds_partition_prefix

logging.basicConfig()


class TestPowerOffTunableLaser(
    standardscripts.BaseScriptTestCase, unittest.IsolatedAsyncioTestCase
):
    async def basic_make_script(self, index):
        self.script = PowerOffTunableLaser(index=index)

        self.laser_state = types.SimpleNamespace(
            detailedState=LaserDetailedState.PROPAGATING_CONTINUOUS_MODE
        )
        self.optical_config_state = types.SimpleNamespace(
            configuration=LaserOpticalConfiguration.NO_SCU
        )

        await self.configure_mocks()

        return [
            self.script,
        ]

    async def mock_setup_laser(
        self, mode, wavelength, optical_configuration, use_projector
    ):
        self.laser_state = types.SimpleNamespace(detailedState=mode)
        self.optical_config_state = types.SimpleNamespace(
            configuration=optical_configuration
        )
        self.script.optical_configuration = optical_configuration
        self.script.wavelength = wavelength

    async def mock_laser_stop_propagate(self, *args, **kwargs):
        self.laser_state = types.SimpleNamespace(
            detailedState=LaserDetailedState.NONPROPAGATING_CONTINUOUS_MODE
        )

    async def configure_mocks(self):
        self.script.laser = unittest.mock.AsyncMock()
        self.script.laser.start_task = utils.make_done_future()
        # Mock evt_summaryState.aget to return ENABLED state
        self.script.laser.evt_summaryState = unittest.mock.MagicMock()
        self.script.laser.evt_summaryState.aget = unittest.mock.AsyncMock(
            return_value=types.SimpleNamespace(summaryState=salobj.State.ENABLED)
        )

        # Mock MTCalsys
        self.script.mtcalsys = unittest.mock.MagicMock()
        self.script.mtcalsys.start_task = utils.make_done_future()
        self.script.mtcalsys.load_calibration_config_file = unittest.mock.MagicMock()
        self.script.mtcalsys.assert_valid_configuration_option = (
            unittest.mock.MagicMock()
        )
        self.script.mtcalsys.get_calibration_configuration = unittest.mock.MagicMock(
            return_value={
                "laser_mode": LaserDetailedState.PROPAGATING_CONTINUOUS_MODE,
                "optical_configuration": LaserOpticalConfiguration.SCU.name,
                "wavelength": 500.0,
            }
        )
        self.script.mtcalsys.setup_laser = unittest.mock.AsyncMock(
            side_effect=self.mock_setup_laser
        )
        self.script.mtcalsys.get_laser_parameters = unittest.mock.AsyncMock(
            return_value=[
                "optical_configuration",
                500.0,
                "interlock",
                "burst_mode",
                "cont_mode",
            ]
        )
        self.script.mtcalsys.laser_stop_propagate = unittest.mock.AsyncMock(
            side_effect=self.mock_laser_stop_propagate
        )

        self.script.laser.configure_mock(
            **{
                "evt_summaryState.aget.side_effect": self.mock_get_laser_summary_state,
                "cmd_setOpticalConfiguration.set_start.side_effect": self.mock_set_optical_config,
                "cmd_setContinuousMode.start.side_effect": self.mock_set_continuous_mode,
                "cmd_startPropagateLaser.start.side_effect": self.mock_stop_laser,
            }
        )

    async def mock_get_laser_summary_state(self, **kwargs):
        return types.SimpleNamespace(summaryState=salobj.State.ENABLED)

    async def mock_set_optical_config(self, **kwargs):
        self.optical_config_state = types.SimpleNamespace(configuration="SCU")

    async def mock_set_continuous_mode(self, **kwargs):
        self.laser_state = types.SimpleNamespace(
            detailedState=LaserDetailedState.NONPROPAGATING_CONTINUOUS_MODE
        )

    async def mock_stop_laser(self, **kwargs):
        self.laser_state = types.SimpleNamespace(
            detailedState=LaserDetailedState.NONROPAGATING_CONTINUOUS_MODE
        )

    async def test_configure(self):
        # Try to configure with only some of the optional parameters
        async with self.make_script():
            mode = LaserDetailedState.PROPAGATING_CONTINUOUS_MODE
            optical_configuration = LaserOpticalConfiguration.SCU.name
            wavelength = 500.0

            await self.configure_script()

            assert self.script.laser_mode == mode
            assert self.script.optical_configuration == optical_configuration
            assert self.script.wavelength == wavelength

    async def test_run_without_failures(self):
        async with self.make_script():
            await self.configure_script()

            await self.run_script()

            # Summary State
            self.script.laser.evt_summaryState.aget.assert_awaited_once_with()

            # Assert states are OK
            assert (
                self.laser_state.detailedState
                == LaserDetailedState.NONPROPAGATING_CONTINUOUS_MODE
            )
            assert (
                self.script.optical_configuration == LaserOpticalConfiguration.SCU.name
            )
            assert self.script.wavelength == 500.0

    async def test_executable(self):
        scripts_dir = standardscripts.get_scripts_dir()
        script_path = os.path.join(
            scripts_dir, "maintel", "calibration", "power_off_tunablelaser.py"
        )
        await self.check_executable(script_path)


if __name__ == "__main__":
    unittest.main()
