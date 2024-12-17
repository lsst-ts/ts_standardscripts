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
from lsst.ts.auxtel.standardscripts.prepare_for import PrepareForFlat
from lsst.ts.observatory.control.mock import ATCSMock

random.seed(47)  # for set_random_lsst_dds_partition_prefix

logging.basicConfig()


class TestPrepareForFlat(
    standardscripts.BaseScriptTestCase, unittest.IsolatedAsyncioTestCase
):
    async def basic_make_script(self, index):
        self.script = PrepareForFlat(index=index)
        self.atcs_mock = ATCSMock()

        return (self.script, self.atcs_mock)

    async def test_run(self):
        async with self.make_script():
            await self.configure_script()

            # TODO: Have to think about how to test this script.

            # await self.run_script()

    async def test_executable(self):
        scripts_dir = get_scripts_dir()
        script_path = scripts_dir / "prepare_for" / "flat.py"
        await self.check_executable(script_path)


if __name__ == "__main__":
    unittest.main()
