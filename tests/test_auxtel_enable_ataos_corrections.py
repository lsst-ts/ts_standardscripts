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

import logging
import random
import unittest

from lsst.ts import standardscripts
from lsst.ts.auxtel.standardscripts import EnableATAOSCorrections, get_scripts_dir
from lsst.ts.observatory.control.mock import ATCSMock

random.seed(47)  # for set_random_lsst_dds_partition_prefix

logging.basicConfig()


class TestEnableATAOSCorrections(
    standardscripts.BaseScriptTestCase, unittest.IsolatedAsyncioTestCase
):
    async def basic_make_script(self, index):
        self.script = EnableATAOSCorrections(index=index)
        self.atcs_mock = ATCSMock()

        return (self.script, self.atcs_mock)

    async def test_run(self):
        async with self.make_script():
            await self.configure_script()
            await self.script.atcs.enable()

            await self.run_script()

            # Testing only corrections enabled by atcs.enable_ataos_corrections
            assert self.atcs_mock.ataos.evt_correctionEnabled.data.m1
            assert self.atcs_mock.ataos.evt_correctionEnabled.data.hexapod
            assert self.atcs_mock.ataos.evt_correctionEnabled.data.atspectrograph

    async def test_executable(self):
        scripts_dir = get_scripts_dir()
        script_path = scripts_dir / "enable_ataos_corrections.py"
        await self.check_executable(script_path)

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
