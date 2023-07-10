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
import random
import unittest
import types
import asyncio

from lsst.ts import salobj, utils

from lsst.ts import standardscripts
from lsst.ts.standardscripts.auxtel.calibrations import PowerOnATCalSys
from lsst.ts.idl.enums import ATWhiteLight, ATMonochromator


random.seed(47)  # for set_random_lsst_dds_partition_prefix

logging.basicConfig()


class TestPowerOnATCalSys(
    standardscripts.BaseScriptTestCase, unittest.IsolatedAsyncioTestCase
):
    async def basic_make_script(self, index):
        self.script = PowerOnATCalSys(index=index, add_remotes=False)

        self.chiller_status = types.SimpleNamespace(chillerState="NOTREADY")
        self.lamp_state = types.SimpleNamespace(
            basicState=ATWhiteLight.LampBasicState.OFF
        )
        self.shutter_status = types.SimpleNamespace(
            shutterState=ATWhiteLight.ShutterState.CLOSED
        )
        self.grating_status = types.SimpleNamespace(
            gratingtype=ATMonochromator.Grating.BLUE
        )

        self.wavelength_status = types.SimpleNamespace(wavelength=200)

        self.slit_status = types.SimpleNamespace(width=0)

        await self.configure_mocks()

        return [
            self.script,
        ]

    async def configure_mocks(self):
        self.script.white_light_source = unittest.mock.AsyncMock()
        self.script.white_light_source.start_task = utils.make_done_future()
        self.script.monochromator = unittest.mock.AsyncMock()
        self.script.monochromator.start_task = utils.make_done_future()

        # Configure mocks

        self.script.white_light_source.configure_mock(
            **{
                "evt_summaryState.aget.side_effect": self.mock_get_whitelightsource_summary_state,
                "cmd_setChillerTemperature.set_start.side_effect": self.mock_start_chiller_temp,
                "cmd_startChiller.start.side_effect": self.mock_get_chiller_status,
                "cmd_openShutter.start.side_effect": self.mock_open_shutter,
                "cmd_turnLampOn.set_start.side_effect": self.mock_get_lamp_status,
            }
        )
        self.script.monochromator.configure_mock(
            **{
                "evt_summaryState.aget.side_effect": self.mock_get_monochromator_summary_state,
                "cmd_selectGrating.set_start.side_effect": self.mock_change_grating,
                "cmd_changeWavelength.set_start.side_effect": self.mock_change_wavelength,
                "cmd_changeSlitWidth.set_start.side_effect": self.mock_change_slit_width,
            }
        )

        # Mock check methods
        self.script.wait_for_lamp_to_warm_up = unittest.mock.AsyncMock(
            side_effect=self.mock_lamp_temp
        )

        self.script.wait_for_chiller_temp_within_tolerance = unittest.mock.AsyncMock(
            side_effect=self.mock_chiller_temp
        )

    # White lamp
    async def mock_get_whitelightsource_summary_state(self, **kwargs):
        return types.SimpleNamespace(summaryState=salobj.State.ENABLED)

    # Chiller
    async def mock_start_chiller_temp(self, **kwargs):
        self.start_chiller_temperature = 30

    async def mock_get_chiller_status(self, **kwargs):
        await asyncio.sleep(0.5)
        return self.chiller_status

    async def mock_chiller_temp(self, **kwargs):
        self.chiller_status = types.SimpleNamespace(chillerState="NOTREADY")
        await asyncio.sleep(5.0)
        self.chiller_status = types.SimpleNamespace(chillerState="READY")

    # Shutter
    async def mock_open_shutter(self, **kwargs):
        self.shutter_status = types.SimpleNamespace(
            shutterState=ATWhiteLight.ShutterState.OPEN
        )

    # Lamp

    async def mock_get_lamp_status(self, **kwargs):
        await asyncio.sleep(0.5)
        return self.lamp_state

    async def mock_lamp_temp(self, **kwargs):
        self.lamp_state.basicState = ATWhiteLight.LampBasicState.WARMUP
        await asyncio.sleep(10.0)
        self.lamp_state.basicState = ATWhiteLight.LampBasicState.ON

    # Monochromator
    async def mock_get_monochromator_summary_state(self, **kwargs):
        return types.SimpleNamespace(summaryState=salobj.State.ENABLED)

    async def mock_change_grating(self, **kwargs):
        self.grating_status = types.SimpleNamespace(
            gratingState=self.script.grating_type
        )

    async def mock_change_wavelength(self, **kwargs):
        self.wavelength_status = types.SimpleNamespace(
            wavelength=self.script.wavelength
        )

    async def mock_change_slit_width(self, **kwargs):
        self.slit_status = types.SimpleNamespace(width=self.script.entrance_slit_width)

    async def test_configure(self):
        # Try to configure with only some of the optional parameters
        async with self.make_script():
            chiller_temperature = 15
            grating_type = 0
            entrance_slit_width = 5

            await self.configure_script(
                chiller_temperature=chiller_temperature,
                grating_type=grating_type,
                entrance_slit_width=entrance_slit_width,
            )

            assert self.script.chiller_temperature == chiller_temperature
            assert self.script.grating_type == grating_type
            assert self.script.entrance_slit_width == entrance_slit_width

    async def test_run_without_without_failures(self):
        async with self.make_script():
            await self.configure_script()

            await self.run_script()

            # Chiller
            self.script.white_light_source.cmd_setChillerTemperature.set_start.assert_awaited_once_with(
                temperature=self.script.chiller_temperature,
                timeout=self.script.cmd_timeout,
            )

            self.script.white_light_source.cmd_startChiller.start.assert_awaited_once_with(
                timeout=self.script.timeout_chiller_cool_down
            )

            self.script.wait_for_chiller_temp_within_tolerance.assert_awaited_once()

            # Shutter
            self.script.white_light_source.cmd_closeShutter.start.assert_awaited_with(
                timeout=self.script.timeout_open_shutter,
            )

            # White lamp
            self.script.white_light_source.cmd_turnLampOn.set_start.assert_awaited_with(
                power=self.script.whitelight_power,
                timeout=self.script.timeout_lamp_warm_up,
            )

            self.script.wait_for_lamp_to_warm_up.assert_awaited_once()

            # Monochromator configuration
            self.script.monochromator.cmd_selectGrating.set_start.assert_awaited_once_with(
                gratingType=self.script.grating_type, timeout=self.script.cmd_timeout
            )

            self.script.monochromator.cmd_changeWavelength.set_start.assert_awaited_once_with(
                wavelength=self.script.wavelength, timeout=self.script.cmd_timeout
            )

            expected_awaits = len(
                [
                    unittest.mock.call(
                        slit=1,
                        slitWidth=self.script.exit_slit_width,
                        timeout=self.script.cmd_timeout,
                    ),
                    unittest.mock.call(
                        slit=2,
                        slitWidth=self.script.exit_slit_width,
                        timeout=self.script.cmd_timeout,
                    ),
                ]
            )

            assert (
                self.script.monochromator.cmd_changeSlitWidth.set_start.await_count
                == expected_awaits
            )

            # Summary State
            self.script.white_light_source.evt_summaryState.aget.assert_awaited_once_with()
            self.script.monochromator.evt_summaryState.aget.assert_awaited_once_with()

            # Assert states are OK
            assert self.chiller_status.chillerState == "READY"
            assert self.lamp_state.basicState == ATWhiteLight.LampBasicState.ON
            assert self.shutter_status.shutterState == ATWhiteLight.ShutterState.OPEN
            assert self.grating_status.gratingState == ATMonochromator.Grating.MIRROR

    async def test_executable(self):
        scripts_dir = standardscripts.get_scripts_dir()
        script_path = scripts_dir / "auxtel" / "calibrations" / "power_on_atcalsys.py"
        await self.check_executable(script_path)


if __name__ == "__main__":
    unittest.main()
