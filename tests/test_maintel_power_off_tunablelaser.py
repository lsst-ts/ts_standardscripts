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

from lsst.ts import salobj, standardscripts, utils
from lsst.ts.standardscripts.maintel.calibration import PowerOffTunableLaser
from lsst.ts.xml.enums.TunableLaser import LaserDetailedState

random.seed(47)  # for set_random_lsst_dds_partition_prefix

logging.basicConfig()


class TestPowerOffTunableLaser(
    standardscripts.BaseScriptTestCase, unittest.IsolatedAsyncioTestCase
):
    async def basic_make_script(self, index):
        self.script = PowerOffTunableLaser(index=index)

        await self.configure_mocks()

        return [
            self.script,
        ]

    async def configure_mocks(self):
        self.script.laser = unittest.mock.AsyncMock()
        self.script.laser.start_task = utils.make_done_future()

        # Configure mocks

        self.script.laser.configure_mock(
            **{
                "evt_summaryState.aget.side_effect": self.mock_get_laser_summary_state,
                "cmd_stopPropagateLaser.start.side_effect": self.mock_stop_laser,
            }
        )

    async def mock_get_laser_summary_state(self, **kwargs):
        return types.SimpleNamespace(summaryState=salobj.State.ENABLED)

    async def mock_stop_laser(self, **kwargs):
        self.laser_state = types.SimpleNamespace(
            detailedState=LaserDetailedState.PROPAGATING_CONTINUOUS_MODE
        )

    async def test_run_without_failures(self):
        async with self.make_script():
            await self.configure_script()

            await self.run_script()

            self.script.laser.cmd_stopPropagateLaser.start.assert_awaited_with(
                timeout=self.script.laser_warmup,
            )

            # Summary State
            self.script.laser.evt_summaryState.aget.assert_awaited_once_with()

            # Assert states are OK
            assert (
                self.laser_status.detailedState
                == LaserDetailedState.NONPROPAGATING_CONTINUOUS_MODE
            )

    async def test_executable(self):
        scripts_dir = standardscripts.get_scripts_dir()
        script_path = os.path.join(
            scripts_dir, "maintel", "calibration", "power_off_tunablelaser.py"
        )
        await self.check_executable(script_path)


if __name__ == "__main__":
    unittest.main()
