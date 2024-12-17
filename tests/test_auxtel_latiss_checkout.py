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
from lsst.ts.auxtel.standardscripts.daytime_checkout import LatissCheckout
from lsst.ts.standardscripts import BaseScriptTestCase


class TestLatissCheckout(BaseScriptTestCase, unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        self.ingest_event_status = 0
        self.ingest_time = time.time()
        self.obsid = "test_obs"
        self.available_instrument_setup = ["filter_list", "grating_list"]
        self.latiss_setup = ["test_filter", "test_grating", 67.0]
        return super().setUp()

    async def basic_make_script(self, index):
        self.script = LatissCheckout(index=index, add_remotes=False)

        return (self.script,)

    async def test_executable(self):
        scripts_dir = get_scripts_dir()
        script_path = scripts_dir / "daytime_checkout" / "latiss_checkout.py"
        print(script_path)
        await self.check_executable(script_path)

    async def get_available_instrument_setup(self):
        return self.available_instrument_setup

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

    @contextlib.asynccontextmanager
    async def setup_mocks(self):
        self.script.latiss.take_bias = unittest.mock.AsyncMock()
        self.script.latiss.take_engtest = unittest.mock.AsyncMock()
        self.script.latiss.setup_instrument = unittest.mock.AsyncMock()

        self.script.latiss.rem = types.SimpleNamespace(
            atoods=unittest.mock.AsyncMock(),
            atspectrograph=unittest.mock.AsyncMock(),
        )
        self.script.latiss.rem.atoods.configure_mock(
            **{"evt_imageInOODS.next.side_effect": self.get_atoods_ingest_event}
        )

        self.script.latiss.get_available_instrument_setup = unittest.mock.AsyncMock(
            side_effect=self.get_available_instrument_setup
        )

        self.script.latiss.get_setup = unittest.mock.AsyncMock(
            side_effect=self.get_latiss_setup
        )

        yield

    async def test_run_script_without_failures(self):
        async with self.make_script(), self.setup_mocks():
            await self.configure_script()

            await self.run_script()

            self.script.latiss.setup_instrument.assert_not_awaited()
            self.script.latiss.take_bias.assert_awaited_once()
            self.script.latiss.take_engtest.assert_awaited_once()

    async def test_run_script_with_ingest_failure(self):
        async with self.make_script(), self.setup_mocks():
            await self.configure_script()

            self.script.latiss.rem.atoods.configure_mock(
                **{"evt_imageInOODS.next.side_effect": asyncio.TimeoutError}
            )

            with pytest.raises(AssertionError):
                await self.run_script()

            self.script.latiss.take_bias.assert_awaited_once()
            self.script.latiss.take_engtest.assert_not_awaited()

    async def test_run_script_with_linear_stage_out_of_position(self):
        async with self.make_script(), self.setup_mocks():
            await self.configure_script()

            self.latiss_setup = ["test_filter", "test_grating", 0.0]

            await self.run_script()

            self.script.latiss.setup_instrument.assert_awaited_once_with(
                linear_stage=self.script.linear_stage_nominal_position
            )
            self.script.latiss.take_bias.assert_awaited_once()
            self.script.latiss.take_engtest.assert_awaited_once()


if __name__ == "__main__":
    unittest.main()
