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
import types
import unittest

from lsst.ts.auxtel.standardscripts import get_scripts_dir
from lsst.ts.auxtel.standardscripts.daytime_checkout import TelescopeAndDomeCheckout
from lsst.ts.standardscripts import BaseScriptTestCase


class TestTelescopeAndDomeCheckout(
    BaseScriptTestCase, unittest.IsolatedAsyncioTestCase
):
    def setUp(self) -> None:
        self.dome_park_az = 285.0
        self.dome_azimuth_position = 0.0
        self.d_az = 15.0
        return super().setUp()

    async def basic_make_script(self, index):
        self.script = TelescopeAndDomeCheckout(index=index, add_remotes=False)
        return [
            self.script,
        ]

    async def get_tel_position(self, flush, timeout):
        if flush:
            await asyncio.sleep(timeout / 2.0)
        return types.SimpleNamespace(
            azimuthPosition=self.dome_azimuth_position,
        )

    @contextlib.asynccontextmanager
    async def setup_mocks(self):
        self.script.atcs.disable_dome_following = unittest.mock.AsyncMock()
        self.script.atcs.slew_icrs = unittest.mock.AsyncMock()
        self.script.atcs.point_azel = unittest.mock.AsyncMock()
        self.script.atcs.stop_tracking = unittest.mock.AsyncMock()
        self.script.atcs.check_tracking = unittest.mock.AsyncMock()
        self.script.atcs.slew_dome_to = unittest.mock.AsyncMock()
        self.script.atcs.home_dome = unittest.mock.AsyncMock()

        self.script.atcs.rem = types.SimpleNamespace(atdome=unittest.mock.AsyncMock())
        self.script.atcs.rem.atdome.configure_mock(
            **{
                "tel_position.next.side_effect": self.get_tel_position,
            }
        )

        yield

    async def test_executable(self):
        scripts_dir = get_scripts_dir()
        script_path = (
            scripts_dir / "daytime_checkout" / "telescope_and_dome_checkout.py"
        )
        print(script_path)
        await self.check_executable(script_path)

    async def test_run_script_without_failures(self):
        async with self.make_script(), self.setup_mocks():
            await self.configure_script()

            await self.run_script()

            slew_dome_to_expected_calls = [
                unittest.mock.call(self.dome_azimuth_position + self.d_az),
                unittest.mock.call(az=self.dome_park_az),
            ]

            self.script.atcs.disable_dome_following.assert_awaited_once()
            self.script.atcs.slew_dome_to.assert_has_awaits(slew_dome_to_expected_calls)


if __name__ == "__main__":
    unittest.main()
