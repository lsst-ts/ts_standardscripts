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
import logging
import random
import unittest

import pytest
from lsst.ts import salobj, standardscripts
from lsst.ts.auxtel.standardscripts import get_scripts_dir
from lsst.ts.auxtel.standardscripts.prepare_for import PrepareForCO2Cleanup

random.seed(47)  # for set_random_lsst_dds_partition_prefix

logging.basicConfig()


class TestPrepareForCO2Cleanup(
    standardscripts.BaseScriptTestCase, unittest.IsolatedAsyncioTestCase
):
    async def basic_make_script(self, index):
        self.script = PrepareForCO2Cleanup(index=index)

        return (self.script,)

    @contextlib.asynccontextmanager
    async def make_dry_script(self):
        async with self.make_script(self):
            self.script.atcs = unittest.mock.AsyncMock()
            self.script.atcs.assert_all_enabled = unittest.mock.AsyncMock()
            self.script.atcs.open_m1_cover = unittest.mock.AsyncMock()
            self.script.atcs.enable_ataos_corrections = unittest.mock.AsyncMock()
            self.script.atcs.point_azel = unittest.mock.AsyncMock()
            self.script.atcs.disable_ataos_corrections = unittest.mock.AsyncMock()
            yield

    async def test_run(self):
        async with self.make_dry_script():
            configuration = dict(
                az=0.0,
                el=80.0,
                rot_tel=0.0,
                target_name="CO2 cleanup position",
                wait_dome=False,
                slew_timeout=180,
            )
            await self.configure_script(**configuration)

            await self.run_script()
            self.script.atcs.assert_all_enabled.assert_awaited_once()
            self.script.atcs.open_m1_cover.assert_awaited_once()
            self.script.atcs.enable_ataos_corrections.assert_awaited_once()
            self.script.atcs.point_azel.assert_awaited_once()
            self.script.atcs.point_azel.assert_called_with(
                az=configuration["az"],
                el=configuration["el"],
                rot_tel=configuration["rot_tel"],
                target_name=configuration["target_name"],
                wait_dome=configuration["wait_dome"],
                slew_timeout=configuration["slew_timeout"],
            )
            self.script.atcs.disable_ataos_corrections.assert_awaited_once()

    async def test_run_all_defaults(self):
        async with self.make_dry_script():
            expected_config = dict(
                az=0.0,
                el=20.0,
                rot_tel=0.0,
                target_name="CO2 cleanup position",
                wait_dome=False,
                slew_timeout=180,
            )

            await self.configure_script()
            await self.run_script()
            self.script.atcs.point_azel.assert_awaited_once()
            self.script.atcs.point_azel.assert_called_with(
                az=expected_config["az"],
                el=expected_config["el"],
                rot_tel=expected_config["rot_tel"],
                target_name=expected_config["target_name"],
                wait_dome=expected_config["wait_dome"],
                slew_timeout=expected_config["slew_timeout"],
            )

    async def test_executable(self):
        scripts_dir = get_scripts_dir()
        script_path = scripts_dir / "prepare_for" / "co2_cleanup.py"
        await self.check_executable(script_path)

    async def test_configure_fail_invalid_el_min(self):
        el = -0.1
        async with self.make_dry_script():
            with pytest.raises(salobj.ExpectedError):
                await self.configure_script(el=el)

    async def test_configure_fail_invalid_el_max(self):
        el = 90.1
        async with self.make_dry_script():
            with pytest.raises(salobj.ExpectedError):
                await self.configure_script(el=el)

    async def test_configure_ignore(self):
        async with self.make_script():
            components = ["atmcs"]
            await self.configure_script(ignore=components)

            assert self.script.atcs.check.atmcs is False

    async def test_configure_ignore_not_atcs_component(self):
        async with self.make_script():
            components = ["not_atcs_comp", "atmcs"]
            await self.configure_script(ignore=components)

            assert hasattr(self.script.atcs, "not_atcs_comp") is False
            assert self.script.atcs.check.atmcs is False


if __name__ == "__main__":
    unittest.main()
