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

import logging
import random
import unittest

from lsst.ts import standardscripts
from lsst.ts.observatory.control.auxtel import ATCS, LATISS, ATCSUsages, LATISSUsages
from lsst.ts.standardscripts.auxtel.prepare_for import PrepareForOnSky

random.seed(47)  # for set_random_lsst_dds_partition_prefix

logging.basicConfig()


class TestPrepareForOnSky(
    standardscripts.BaseScriptTestCase, unittest.IsolatedAsyncioTestCase
):
    async def basic_make_script(self, index):
        self.script = PrepareForOnSky(index=index)
        self.script.atcs = ATCS(
            domain=self.script.domain,
            log=self.script.log,
            intended_usage=ATCSUsages.DryTest,
        )
        self.script.latiss = LATISS(
            domain=self.script.domain,
            log=self.script.log,
            intended_usage=LATISSUsages.DryTest,
        )
        self.script.atcs.disable_checks_for_components = unittest.mock.Mock()
        self.script.latiss.disable_checks_for_components = unittest.mock.Mock()

        return (self.script,)

    async def test_configure(self):
        async with self.make_script():
            # works with no configuration
            await self.configure_script()

    async def test_configure_ignore(self):
        async with self.make_script():
            components = ["atpneumatics", "ataos", "atspectrograph"]
            await self.configure_script(ignore=components)

            self.script.atcs.disable_checks_for_components.assert_called_once_with(
                components=components
            )

            self.script.latiss.disable_checks_for_components.assert_called_once_with(
                components=components
            )

    async def test_executable(self):
        scripts_dir = standardscripts.get_scripts_dir()
        script_path = scripts_dir / "auxtel" / "prepare_for" / "onsky.py"
        await self.check_executable(script_path)


if __name__ == "__main__":
    unittest.main()
