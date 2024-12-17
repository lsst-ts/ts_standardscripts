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
from lsst.ts.auxtel.standardscripts import get_scripts_dir
from lsst.ts.auxtel.standardscripts.prepare_for import PrepareForOnSky
from lsst.ts.observatory.control.auxtel import ATCS, LATISS, ATCSUsages, LATISSUsages

random.seed(47)  # for set_random_lsst_dds_partition_prefix

logging.basicConfig()


class TestPrepareForOnSky(
    standardscripts.BaseScriptTestCase, unittest.IsolatedAsyncioTestCase
):
    async def basic_make_script(self, index):
        self.script = PrepareForOnSky(index=index)
        self.script.attcs = ATCS(
            domain=self.script.domain,
            log=self.script.log,
            intended_usage=ATCSUsages.DryTest,
        )
        self.script.latiss = LATISS(
            domain=self.script.domain,
            log=self.script.log,
            intended_usage=LATISSUsages.DryTest,
        )

        return (self.script,)

    async def test_configure(self):
        async with self.make_script():
            # works with no configuration
            await self.configure_script()

    async def test_configure_ignore(self):
        async with self.make_script():
            await self.configure_script(
                ignore=["atpneumatics", "ataos", "atspectrograph"]
            )

            assert not self.script.attcs.check.atpneumatics
            assert not self.script.attcs.check.ataos
            assert not self.script.latiss.check.atspectrograph

    async def test_configure_ignore_inexistent(self):
        async with self.make_script():
            with self.assertLogs(self.script.log, level=logging.WARNING) as script_logs:
                await self.configure_script(ignore=["nonono"])

            expected_warning_msg = (
                f"WARNING:Script:Component nonono not in CSC Group. "
                f"Must be one of {self.script.attcs.components_attr} or "
                f"{self.script.latiss.components_attr}. Ignoring."
            )

            assert expected_warning_msg in script_logs.output

    async def test_executable(self):
        scripts_dir = get_scripts_dir()
        script_path = scripts_dir / "prepare_for" / "onsky.py"
        await self.check_executable(script_path)


if __name__ == "__main__":
    unittest.main()
