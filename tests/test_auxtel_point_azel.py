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

import contextlib
import unittest

import pytest
from lsst.ts import salobj
from lsst.ts.auxtel.standardscripts import PointAzEl, get_scripts_dir
from lsst.ts.standardscripts import BaseScriptTestCase


class TestPointAzEl(BaseScriptTestCase, unittest.IsolatedAsyncioTestCase):
    async def basic_make_script(self, index):
        self.script = PointAzEl(index=index)

        return (self.script,)

    @contextlib.asynccontextmanager
    async def make_dry_script(self):
        async with self.make_script():
            self.script.atcs = unittest.mock.AsyncMock()
            self.script.atcs.components_attr = ["athexapod"]

            self.script.atcs.assert_all_enabled = unittest.mock.AsyncMock()
            self.script.atcs.point_azel = unittest.mock.AsyncMock()
            self.script.atcs.stop_tracking = unittest.mock.AsyncMock()
            self.script.configure_tcs = unittest.mock.AsyncMock()

            yield

    async def test_config_fail_no_defaults(self) -> None:
        async with self.make_dry_script():
            with pytest.raises(salobj.ExpectedError):
                await self.configure_script()

            self.script.configure_tcs.assert_not_called()

    async def test_config_fail_az_no_el(self) -> None:
        async with self.make_dry_script():
            with pytest.raises(
                salobj.ExpectedError, match="'el' is a required property"
            ):
                await self.configure_script(az=0.0)

            self.script.configure_tcs.assert_not_called()

    async def test_config_fail_el_no_az(self) -> None:
        async with self.make_dry_script():
            with pytest.raises(
                salobj.ExpectedError, match="'az' is a required property"
            ):
                await self.configure_script(el=0.0)
            self.script.configure_tcs.assert_not_called()

    async def test_configure_fail_invalid_el_min(self):
        az = 0.0
        el = -0.1
        async with self.make_dry_script():
            with pytest.raises(salobj.ExpectedError):
                await self.configure_script(el=el, az=az)
            self.script.configure_tcs.assert_not_called()

    async def test_configure_fail_invalid_el_max(self):
        az = 0.0
        el = 90.1
        async with self.make_dry_script():
            with pytest.raises(salobj.ExpectedError):
                await self.configure_script(el=el, az=az)
            self.script.configure_tcs.assert_not_called()

    async def test_config_ignore(self) -> None:
        async with self.make_dry_script():
            az = 0.0
            el = 80.0
            ignore = ["athexapod", "no_comp"]

            await self.configure_script(az=az, el=el, ignore=ignore)
            assert self.script.atcs.check.athexapod is False
            self.script.atcs.check.no_comp.assert_not_called()
            self.script.configure_tcs.assert_awaited_once()

    @unittest.mock.patch(
        "lsst.ts.standardscripts.BaseBlockScript.obs_id", "202306060001"
    )
    async def test_configure_with_program_reason(self):
        """Testing a valid configuration: with program and reason"""

        async with self.make_dry_script():
            self.script.get_obs_id = unittest.mock.AsyncMock(
                side_effect=["202306060001"]
            )

            az = 0.0
            el = 80.0
            program = "BLOCK-123"
            reason = "SITCOM-321"
            await self.configure_script(
                az=az,
                el=el,
                program=program,
                reason=reason,
            )

            assert self.script.program == program
            assert self.script.reason == reason
            assert (
                self.script.checkpoint_message
                == "PointAzEl BLOCK-123 202306060001 SITCOM-321"
            )
            self.script.configure_tcs.assert_awaited_once()

    async def test_run_azel(self):
        async with self.make_dry_script():
            self.script.get_obs_id = unittest.mock.AsyncMock(
                side_effect=["202306060001"]
            )

            az = 0.0
            el = 80.0
            rot_tel = 0.0
            target_name = "eta Car"
            wait_dome = False
            slew_timeout = 240.0
            program = "BLOCK-123"
            reason = "SITCOM-321"

            await self.configure_script(
                az=az,
                el=el,
                rot_tel=rot_tel,
                target_name=target_name,
                wait_dome=wait_dome,
                slew_timeout=slew_timeout,
                program=program,
                reason=reason,
            )

            await self.run_script()

            self.script.configure_tcs.assert_awaited_once()

            self.script.atcs.point_azel.assert_awaited_once()
            self.script.atcs.point_azel.assert_called_with(
                az=az,
                el=el,
                rot_tel=rot_tel,
                target_name=target_name,
                wait_dome=wait_dome,
                slew_timeout=slew_timeout,
            )

    async def test_run_point_azel_fails(self):
        async with self.make_dry_script():
            self.script.atcs.point_azel = unittest.mock.AsyncMock(
                side_effect=RuntimeError
            )

            await self.configure_script(az=0.0, el=80.0)

            with pytest.raises(AssertionError):
                await self.run_script()

            self.script.atcs.point_azel.assert_awaited_once()
            self.script.tcs.stop_tracking.assert_awaited_once()

    async def test_executable(self):
        scripts_dir = get_scripts_dir()
        script_path = scripts_dir / "point_azel.py"
        await self.check_executable(script_path)


if __name__ == "__main__":
    unittest.main()
