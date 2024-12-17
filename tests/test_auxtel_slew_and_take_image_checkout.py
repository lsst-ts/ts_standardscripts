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
from lsst.ts.auxtel.standardscripts.daytime_checkout import SlewAndTakeImageCheckout
from lsst.ts.idl.enums.ATMCS import M3State
from lsst.ts.standardscripts import BaseScriptTestCase


class TestSlewAndTakeImageCheckout(
    BaseScriptTestCase, unittest.IsolatedAsyncioTestCase
):
    def setUp(self) -> None:
        self.ingest_event_status = 0
        self.ingest_time = time.time()
        self.obsid = "test_obs"
        self.latiss_setup = ["test_filter", "test_grating"]
        self.dome_park_az = 285.0
        self.ataos_correction_status = True
        self.ataos_correction_result = "enabled"
        self.cmd_time = time.time()
        self.m3_state_latiss_port = M3State.NASMYTH2
        return super().setUp()

    async def basic_make_script(self, index):
        self.script = SlewAndTakeImageCheckout(index=index, add_remotes=False)
        return [
            self.script,
        ]

    async def get_latiss_setup(self):
        return self.latiss_setup

    async def get_atoods_ingest_event(self, flush, timeout):
        if flush:
            await asyncio.sleep(timeout / 2.0)
        return types.SimpleNamespace(
            statusCode=self.ingest_event_status,
            private_sndStamp=self.ingest_time,
            obsid=self.obsid,
        )

    async def get_cmd_enableCorrection(self, m1, hexapod, atspectrograph):
        return types.SimpleNamespace(
            statusCode=self.ataos_correction_status,
            result=self.ataos_correction_result,
            private_sndStamp=self.cmd_time,
        )

    async def get_evt_m3State(self):
        return types.SimpleNamespace(state=self.m3_state_latiss_port)

    @contextlib.asynccontextmanager
    async def setup_mocks(self):
        self.script.atcs.disable_dome_following = unittest.mock.AsyncMock()
        self.script.atcs.slew_icrs = unittest.mock.AsyncMock()
        self.script.atcs.point_azel = unittest.mock.AsyncMock()
        self.script.atcs.stop_tracking = unittest.mock.AsyncMock()
        self.script.atcs.check_tracking = unittest.mock.AsyncMock()
        self.script.atcs.slew_dome_to = unittest.mock.AsyncMock()
        self.script.atcs.close_m1_cover = unittest.mock.AsyncMock()
        self.script.atcs.close_m1_vent = unittest.mock.AsyncMock()

        self.script.latiss.take_engtest = unittest.mock.AsyncMock()
        self.script.latiss.get_setup = unittest.mock.AsyncMock(
            side_effect=self.get_latiss_setup
        )

        self.script.latiss.rem = types.SimpleNamespace(atoods=unittest.mock.AsyncMock())
        self.script.latiss.rem.atoods.configure_mock(
            **{"evt_imageInOODS.next.side_effect": self.get_atoods_ingest_event}
        )
        self.script.atcs.rem = types.SimpleNamespace(
            ataos=unittest.mock.AsyncMock(), atmcs=unittest.mock.AsyncMock()
        )
        self.script.atcs.rem.ataos.configure_mock(
            **{
                "cmd_enableCorrection.set_start.side_effect": self.get_cmd_enableCorrection,
            }
        )
        self.script.atcs.rem.atmcs.configure_mock(
            **{
                "evt_m3State.aget.side_effect": self.get_evt_m3State,
            }
        )

        yield

    async def test_executable(self):
        scripts_dir = get_scripts_dir()
        script_path = (
            scripts_dir / "daytime_checkout" / "slew_and_take_image_checkout.py"
        )
        print(script_path)
        await self.check_executable(script_path)

    async def test_run_script_without_failures(self):
        async with self.make_script(), self.setup_mocks():
            await self.configure_script()

            await self.run_script()

            take_engtest_expected_calls = [
                unittest.mock.call(2, filter=0, grating=0),
                unittest.mock.call(2, filter=1, grating=1),
            ]

            slew_dome_to_expected_calls = [unittest.mock.call(az=self.dome_park_az)]

            self.script.atcs.close_m1_cover.assert_awaited_once()
            self.script.latiss.take_engtest.assert_has_awaits(
                take_engtest_expected_calls
            )
            self.script.atcs.slew_dome_to.assert_has_awaits(slew_dome_to_expected_calls)

    async def test_run_script_with_ingest_failure(self):
        async with self.make_script(), self.setup_mocks():
            await self.configure_script()

            self.script.latiss.rem.atoods.configure_mock(
                **{"evt_imageInOODS.next.side_effect": 1}
            )

            with pytest.raises(AssertionError):
                await self.run_script()

            self.script.atcs.close_m1_cover.assert_awaited_once()
            self.script.latiss.take_engtest.assert_awaited_once()
            self.script.atcs.check_tracking.assert_not_awaited()


if __name__ == "__main__":
    unittest.main()
