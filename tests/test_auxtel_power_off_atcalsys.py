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
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

import asyncio
import logging
import random
import types
import unittest

from lsst.ts import salobj, standardscripts, utils
from lsst.ts.auxtel.standardscripts import get_scripts_dir
from lsst.ts.auxtel.standardscripts.calibrations import PowerOffATCalSys
from lsst.ts.idl.enums import ATWhiteLight

random.seed(47)  # for set_random_lsst_dds_partition_prefix

logging.basicConfig()


class TestPowerOffATCalSys(
    standardscripts.BaseScriptTestCase, unittest.IsolatedAsyncioTestCase
):
    async def basic_make_script(self, index):
        self.script = PowerOffATCalSys(index=index, add_remotes=False)

        self.lamp_state = types.SimpleNamespace(
            basicState=ATWhiteLight.LampBasicState.ON
        )
        self.shutter_status = types.SimpleNamespace(
            shutterState=ATWhiteLight.ShutterState.OPEN
        )

        await self.configure_mocks()

        return [
            self.script,
        ]

    async def configure_mocks(self):
        self.script.white_light_source = unittest.mock.AsyncMock()
        self.script.white_light_source.start_task = utils.make_done_future()

        # Configure mocks

        self.script.white_light_source.configure_mock(
            **{
                "evt_summaryState.aget.side_effect": self.mock_get_whitelightsource_summary_state,
                "cmd_turnLampOff.start.side_effect": self.mock_get_lamp_status,
                "cmd_closeShutter.start.side_effect": self.mock_close_shutter,
            }
        )

        # Mock check methods
        self.script.wait_for_lamp_to_cool_down = unittest.mock.AsyncMock(
            side_effect=self.mock_lamp_temp
        )

    # Summary State

    async def mock_get_whitelightsource_summary_state(self, **kwargs):
        return types.SimpleNamespace(summaryState=salobj.State.ENABLED)

    # Lamp

    async def mock_get_lamp_status(self, **kwargs):
        await asyncio.sleep(0.5)
        return self.lamp_state

    async def mock_lamp_temp(self, **kwargs):
        self.lamp_state.basicState = ATWhiteLight.LampBasicState.TURNING_OFF
        await asyncio.sleep(15.0)
        self.lamp_state.basicState = ATWhiteLight.LampBasicState.OFF

    # Shutter
    async def mock_close_shutter(self, **kwargs):
        types.SimpleNamespace(shutterState=ATWhiteLight.ShutterState.OPEN)
        await asyncio.sleep(3)
        self.shutter_status = types.SimpleNamespace(
            shutterState=ATWhiteLight.ShutterState.CLOSED
        )

    async def test_run_without_without_failures(self):
        async with self.make_script():
            await self.configure_script()

            await self.run_script()

            # Summary State
            self.script.white_light_source.evt_summaryState.aget.assert_awaited_once_with(
                timeout=self.script.cmd_timeout
            )

            # White lamp
            self.script.white_light_source.cmd_turnLampOff.start.assert_awaited_with(
                timeout=self.script.timeout_lamp_cool_down,
            )

            self.script.wait_for_lamp_to_cool_down.assert_awaited_once()

            # Shutter
            self.script.white_light_source.cmd_closeShutter.start.assert_awaited_with(
                timeout=self.script.timeout_close_shutter,
            )

            # Chiller
            self.script.white_light_source.cmd_stopChiller.start.assert_awaited_once_with(
                timeout=self.script.cmd_timeout
            )

            # Check status
            assert self.lamp_state.basicState == ATWhiteLight.LampBasicState.OFF
            assert self.shutter_status.shutterState == ATWhiteLight.ShutterState.CLOSED

    async def test_executable(self):
        scripts_dir = get_scripts_dir()
        script_path = scripts_dir / "calibrations" / "power_off_atcalsys.py"
        await self.check_executable(script_path)


if __name__ == "__main__":
    unittest.main()
