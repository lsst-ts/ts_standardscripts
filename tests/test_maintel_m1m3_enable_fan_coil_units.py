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

import asyncio
import types
import unittest
import warnings

from lsst.ts import salobj
from lsst.ts.observatory.control.maintel.mtcs import MTCS, MTCSUsages
from lsst.ts.standardscripts import BaseScriptTestCase, get_scripts_dir
from lsst.ts.standardscripts.maintel.m1m3 import EnableFanCoilUnits


class TestEnableFanCoilUnits(BaseScriptTestCase, unittest.IsolatedAsyncioTestCase):
    async def basic_make_script(self, index):
        self.script = EnableFanCoilUnits(index=index)
        self.script.mtm1m3ts = unittest.mock.AsyncMock()
        return (self.script,)

    async def test_config_default(self):
        async with self.make_script():
            self.configure_script(foo=None)
            assert False


if __name__ == "__main__":
    unittest.main()
