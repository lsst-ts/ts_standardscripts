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

import unittest

from lsst.ts.standardscripts import BaseScriptTestCase, get_scripts_dir
from lsst.ts.standardscripts.auxtel.daytime_checkout import ATPnuematicsCheckout
import contextlib
import pytest
import types
import asyncio
import time


class TestATPnuematicsCheckout(BaseScriptTestCase, unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        self.tel_mainAirSourcePressure = 400000
        self.tel_m1AirPressure = 400000
        self.cmd_time = time.time()
        self.ataos_correction_status = True
        self.ataos_correction_result = "enabled"
        return super().setUp()

    async def basic_make_script(self, index):
        self.script = ATPnuematicsCheckout(index=index, add_remotes=False)
        return [
            self.script,
        ]

    async def test_executable(self):
        scripts_dir = get_scripts_dir()
        script_path = (
            scripts_dir / "auxtel" / "daytime_checkout" / "atpnuematics_checkout.py"
        )
        print(script_path)
        await self.check_executable(script_path)

    async def get_tel_mainAirSourcePressure(self, flush, timeout):
        if flush:
            await asyncio.sleep(timeout / 2.0)
        return types.SimpleNamespace(
            pressure=self.tel_mainAirSourcePressure,
        )

    async def get_tel_m1AirSourcePressure(self, timeout):
        return types.SimpleNamespace(
            pressure=self.tel_m1AirPressure,
        )

    async def get_cmd_enableCorrection(self, m1, hexapod, atspectrograph):
        return types.SimpleNamespace(
            statusCode=self.ataos_correction_status,
            result=self.ataos_correction_result,
            private_sndStamp=self.cmd_time,
        )

    async def get_cmd_disableCorrection(self, m1, hexapod, atspectrograph):
        return types.SimpleNamespace(
            statusCode=self.ataos_correction_status,
            result=self.ataos_correction_result,
            private_sndStamp=self.cmd_time,
        )

    @contextlib.asynccontextmanager
    async def setup_mocks(self):
        self.script.atcs.open_valves = unittest.mock.AsyncMock()
        self.script.atcs.open_m1_cover = unittest.mock.AsyncMock()
        self.script.atcs.close_m1_cover = unittest.mock.AsyncMock()
        self.script.atcs.open_m1_vent = unittest.mock.AsyncMock()
        self.script.atcs.close_m1_vent = unittest.mock.AsyncMock()

        self.script.atcs.rem = types.SimpleNamespace(
            atpnuematics=unittest.mock.AsyncMock(), ataos=unittest.mock.AsyncMock()
        )
        self.script.atcs.rem.atpnuematics.configure_mock(
            **{
                "tel_mainAirSourcePressure.next.side_effect": self.get_tel_mainAirSourcePressure,
                "tel_m1AirPressure.aget.side_effect": self.get_tel_m1AirSourcePressure,
            }
        )
        self.script.atcs.rem.ataos.configure_mock(
            **{
                "cmd_enableCorrection.set_start.side_effect": self.get_cmd_enableCorrection,
                "cmd_disableCorrection.set_start.side_effect": self.get_cmd_disableCorrection,
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
