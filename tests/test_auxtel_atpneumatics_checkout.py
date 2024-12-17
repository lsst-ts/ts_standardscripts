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

import asyncio
import contextlib
import time
import types
import unittest

import pytest
from lsst.ts.auxtel.standardscripts import get_scripts_dir
from lsst.ts.auxtel.standardscripts.daytime_checkout import ATPneumaticsCheckout
from lsst.ts.observatory.control.auxtel.atcs import ATCS, ATCSUsages
from lsst.ts.standardscripts import BaseScriptTestCase


class TestATPneumaticsCheckout(BaseScriptTestCase, unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        self.tel_mainAirSourcePressure = 400000
        self.tel_m1AirPressure_enabled = 100005
        self.tel_m1AirPressure_commanded = 100000
        self.tel_m1AirPressure_disabled = 0
        self.cmd_time = time.time()
        self.ataos_correction_status = True
        self.ataos_correction_result = "enabled"
        return super().setUp()

    async def basic_make_script(self, index):
        self.script = ATPneumaticsCheckout(index=index)
        return [
            self.script,
        ]

    async def test_executable(self):
        scripts_dir = get_scripts_dir()
        script_path = scripts_dir / "daytime_checkout" / "atpneumatics_checkout.py"
        print(script_path)
        await self.check_executable(script_path)

    async def get_tel_main_air_source_pressure(self, flush, timeout):
        if flush:
            await asyncio.sleep(timeout / 2.0)
        return types.SimpleNamespace(
            pressure=self.tel_mainAirSourcePressure,
        )

    async def get_m1_correction_completed_pressure(self, timeout):
        return types.SimpleNamespace(
            pressure=self.tel_m1AirPressure_commanded,
        )

    async def cmd_enable_corrections(self):
        asyncio.create_task(self.raise_mirror())

    async def cmd_disable_corrections(self):
        asyncio.create_task(self.lower_mirror())

    async def raise_mirror(self):
        self._m1_pressure = self.tel_m1AirPressure_enabled
        await asyncio.sleep(0.5)

    async def lower_mirror(self):
        self._m1_pressure = self.tel_m1AirPressure_disabled
        await asyncio.sleep(0.5)

    async def get_tel_m1_air_pressure(self, timeout):
        await asyncio.sleep(0.1)
        return types.SimpleNamespace(pressure=self._m1_pressure)

    @contextlib.asynccontextmanager
    async def setup_mocks(self):
        self.script.atcs = ATCS(
            domain=self.script.domain,
            intended_usage=ATCSUsages.DryTest,
            log=self.script.log,
        )
        self.script.atcs.open_valves = unittest.mock.AsyncMock()
        self.script.atcs.open_m1_cover = unittest.mock.AsyncMock()
        self.script.atcs.close_m1_cover = unittest.mock.AsyncMock()
        self.script.atcs.open_m1_vent = unittest.mock.AsyncMock()
        self.script.atcs.close_m1_vent = unittest.mock.AsyncMock()
        self.script.atcs.point_azel = unittest.mock.AsyncMock()
        self.script.atcs.stop_tracking = unittest.mock.AsyncMock()

        self.script.atcs.enable_ataos_corrections = unittest.mock.AsyncMock(
            side_effect=self.cmd_enable_corrections
        )
        self.script.atcs.disable_ataos_corrections = unittest.mock.AsyncMock(
            side_effect=self.cmd_disable_corrections
        )

        self.script.atcs.rem = types.SimpleNamespace(
            atpneumatics=unittest.mock.AsyncMock(), ataos=unittest.mock.AsyncMock()
        )
        self.script.atcs.rem.atpneumatics.configure_mock(
            **{
                "tel_mainAirSourcePressure.next.side_effect": self.get_tel_main_air_source_pressure,
                "tel_m1AirPressure.aget.side_effect": self.get_tel_m1_air_pressure,
            }
        )
        self.script.atcs.rem.ataos.configure_mock(
            **{
                "evt_m1CorrectionCompleted.aget.side_effect": self.get_m1_correction_completed_pressure,
            }
        )

        yield

    async def test_run_script_without_failures(self):
        async with self.make_script(), self.setup_mocks():
            await self.configure_script()

            await self.run_script()

            self.script.atcs.open_valves.assert_awaited_once()
            self.script.atcs.open_m1_vent.assert_awaited_once()
            self.script.atcs.close_m1_vent.assert_awaited_once()

    async def test_run_script_with_low_pressure(self):
        async with self.make_script(), self.setup_mocks():
            await self.configure_script()

            self.tel_mainAirSourcePressure = 1

            with pytest.raises(AssertionError):
                await self.run_script()

            self.script.atcs.open_valves.assert_awaited_once()
            self.script.atcs.open_m1_vent.assert_not_awaited()
            self.script.atcs.close_m1_vent.assert_not_awaited()


if __name__ == "__main__":
    unittest.main()
