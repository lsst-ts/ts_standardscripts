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

import pytest
from lsst.ts import standardscripts
from lsst.ts.maintel.standardscripts import Stop

random.seed(47)  # for set_random_lsst_dds_partition_prefix

logging.basicConfig()


class TestStartup(standardscripts.BaseScriptTestCase, unittest.IsolatedAsyncioTestCase):
    async def basic_make_script(self, index):
        self.script = Stop(index=index)

        # TODO DM-25731
        # Update this code to match auxtel/test_stop.py once
        # MCS.stop_all is implemented.
        return (self.script,)

    async def test_run(self):
        async with self.make_script():
            await self.configure_script()
            with pytest.raises(AssertionError):
                await self.run_script()

    async def test_executable(self):
        scripts_dir = standardscripts.get_scripts_dir()
        script_path = scripts_dir / "maintel" / "stop.py"
        await self.check_executable(script_path)


if __name__ == "__main__":
    unittest.main()
