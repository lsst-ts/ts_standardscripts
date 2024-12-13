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
# along with this program. If not, see <https://www.gnu.org/licenses/>.

import contextlib
import unittest

import pytest
from lsst.ts import salobj, standardscripts, utils
from lsst.ts.maintel.standardscripts.disable_hexapod_compensation_mode import (
    DisableHexapodCompensationMode,
)


class TestDisableHexapodCompensationMode(
    standardscripts.BaseScriptTestCase, unittest.IsolatedAsyncioTestCase
):
    async def basic_make_script(self, index):
        self.script = DisableHexapodCompensationMode(index=index)
        self.script.mtcs = unittest.mock.AsyncMock()
        self.script.mtcs.start_task = utils.make_done_future()
        self.script.mtcs.disable_compensation_mode = unittest.mock.AsyncMock()

        return (self.script,)

    @contextlib.asynccontextmanager
    async def make_dry_script(self):
        async with self.make_script():
            self.script.mtcs = unittest.mock.AsyncMock()
            self.script.mtcs.disable_compensation_for_hexapod = (
                unittest.mock.AsyncMock()
            )
            yield

    async def test_configure_good(self):
        async with self.make_dry_script():
            components = ["M2Hexapod", "CameraHexapod"]
            await self.configure_script(components=components)

    async def test_configure_invalid(self):
        async with self.make_dry_script():
            components = ["InvalidComponent"]
            with pytest.raises(salobj.ExpectedError):
                await self.configure_script(components=components)

    @unittest.mock.patch(
        "lsst.ts.standardscripts.BaseBlockScript.obs_id", "202306060001"
    )
    async def test_configure_with_program_reason(self):
        async with self.make_dry_script():
            self.script.get_obs_id = unittest.mock.AsyncMock(
                side_effect=["202306060001"]
            )
            components = ["M2Hexapod", "CameraHexapod"]
            program = "BLOCK-123"
            reason = "SITCOM-321"
            await self.configure_script(
                components=components,
                program=program,
                reason=reason,
            )

            assert self.script.program == program
            assert self.script.reason == reason
            assert (
                self.script.checkpoint_message
                == "DisableHexapodCompensationMode BLOCK-123 202306060001 SITCOM-321"
            )

    async def test_run(self):
        async with self.make_script():
            self.script.get_obs_id = unittest.mock.AsyncMock(
                side_effect=["202306060001"]
            )
            components = ["M2Hexapod", "CameraHexapod"]
            program = "BLOCK-123"
            reason = "SITCOM-321"
            await self.configure_script(
                components=components,
                program=program,
                reason=reason,
            )
            await self.run_script()

            hexapods = [self.script.component_to_hexapod(comp) for comp in components]
            expected_calls = [unittest.mock.call(hexapod) for hexapod in hexapods]

            self.script.mtcs.disable_compensation_mode.assert_has_awaits(
                expected_calls, any_order=True
            )

    async def test_executable(self):
        scripts_dir = standardscripts.get_scripts_dir()
        script_path = scripts_dir / "maintel" / "disable_hexapod_compensation_mode.py"
        print(script_path)
        await self.check_executable(script_path)


if __name__ == "__main__":
    unittest.main()
