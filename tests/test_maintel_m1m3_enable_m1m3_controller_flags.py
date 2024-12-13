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
from lsst.ts.maintel.standardscripts.m1m3 import EnableM1M3SlewControllerFlags


class TestEnableM1M3SlewControllerFlags(
    standardscripts.BaseScriptTestCase, unittest.IsolatedAsyncioTestCase
):
    async def basic_make_script(self, index):
        self.script = EnableM1M3SlewControllerFlags(index=index)
        self.script.mtcs = unittest.mock.AsyncMock()
        self.script.mtcs.start_task = utils.make_done_future()
        self.script.mtcs.set_m1m3_slew_controller_settings = unittest.mock.AsyncMock()
        self.script.mtcs.configure_mock(
            m1m3_in_engineering_mode=self.mock_m1m3_in_engineering_mode
        )

        return (self.script,)

    @contextlib.asynccontextmanager
    async def mock_m1m3_in_engineering_mode(self):
        yield

    @contextlib.asynccontextmanager
    async def make_dry_script(self):
        async with self.make_script():
            self.script.mtcs = unittest.mock.AsyncMock()
            self.script.mtcs.enable_m1m3_slew_controller_flags = (
                unittest.mock.AsyncMock()
            )
            yield

    async def test_configure_default(self):
        async with self.make_dry_script():
            await self.configure_script(slew_flags="default")
            default_flags, default_enables = self.script.get_default_slew_flags()
            assert self.script.config.slew_flags == default_flags
            assert self.script.config.enable == default_enables

    async def test_configure_custom(self):
        custom_settings = {
            "slew_flags": ["ACCELERATIONFORCES", "BALANCEFORCES"],
            "enable": [True, False],
        }
        async with self.make_dry_script():
            await self.configure_script(
                slew_flags=custom_settings["slew_flags"],
                enable=custom_settings["enable"],
            )
            for flag, enable in zip(
                custom_settings["slew_flags"], custom_settings["enable"]
            ):
                assert flag in [f.name for f in self.script.config.slew_flags]
                assert enable in self.script.config.enable

    async def test_invalid_configuration(self):
        async with self.make_dry_script():
            with pytest.raises(
                salobj.ExpectedError,
                match="slew_flags and enable arrays must have the same length.",
            ):
                await self.configure_script(
                    slew_flags=["ACCELERATIONFORCES"], enable=[True, False]
                )

    @unittest.mock.patch(
        "lsst.ts.standardscripts.BaseBlockScript.obs_id", "202306060001"
    )
    async def test_configure_with_program_reason(self):
        async with self.make_dry_script():
            self.script.get_obs_id = unittest.mock.AsyncMock(
                side_effect=["202306060001"]
            )
            program = "BLOCK-123"
            reason = "SITCOM-321"
            custom_settings = {
                "slew_flags": ["ACCELERATIONFORCES", "BALANCEFORCES"],
                "enable": [True, False],
            }
            await self.configure_script(
                slew_flags=custom_settings["slew_flags"],
                enable=custom_settings["enable"],
                program=program,
                reason=reason,
            )

            assert self.script.program == program
            assert self.script.reason == reason
            assert (
                self.script.checkpoint_message
                == "EnableM1M3SlewControllerFlags BLOCK-123 202306060001 SITCOM-321"
            )

    async def test_run(self):

        async with self.make_script():
            custom_settings = {
                "slew_flags": ["ACCELERATIONFORCES", "BALANCEFORCES"],
                "enable": [True, False],
            }
            program = "BLOCK-123"
            reason = "SITCOM-321"

            await self.configure_script(
                slew_flags=custom_settings["slew_flags"],
                enable=custom_settings["enable"],
                program=program,
                reason=reason,
            )

            await self.run_script()

            # Convert flags to enumeration for assertion
            expected_enum_flags = self.script.convert_flag_names_to_enum(
                custom_settings["slew_flags"]
            )

            # Verify mock calls
            expected_calls = [
                unittest.mock.call(flag, enable)
                for flag, enable in zip(expected_enum_flags, custom_settings["enable"])
            ]
            self.script.mtcs.set_m1m3_slew_controller_settings.assert_has_awaits(
                expected_calls
            )

    async def test_executable(self):
        scripts_dir = standardscripts.get_scripts_dir()
        script_path = (
            scripts_dir / "maintel" / "m1m3" / "enable_m1m3_slew_controller_flags.py"
        )
        await self.check_executable(script_path)
