# This file is part of ts_maintel_standardscripts
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

from lsst.ts import standardscripts
from lsst.ts.maintel.standardscripts import OpenMirrorCovers


class TestOpenMirrorCovers(
    standardscripts.BaseScriptTestCase, unittest.IsolatedAsyncioTestCase
):
    async def basic_make_script(self, index):
        self.script = OpenMirrorCovers(index=index)

        return (self.script,)

    @contextlib.asynccontextmanager
    async def make_dry_script(self):
        async with self.make_script(self):
            self.script.mtcs = unittest.mock.AsyncMock()
            self.script.mtcs.assert_all_enabled = unittest.mock.AsyncMock()
            self.script.mtcs.open_m1_cover = unittest.mock.AsyncMock()
            yield

    async def test_run(self):
        async with self.make_dry_script():
            await self.configure_script()

            await self.run_script()
            self.script.mtcs.assert_all_enabled.assert_awaited_once()
            self.script.mtcs.open_m1_cover.assert_awaited_once()

    async def test_configure_ignore(self):
        async with self.make_script():
            components = ["mtptg"]
            await self.configure_script(ignore=components)

            assert self.script.mtcs.check.mtptg is False

    async def test_configure_ignore_not_csc_component(self):
        async with self.make_script():
            components = ["not_csc_comp", "mtptg"]
            await self.configure_script(ignore=components)

            assert hasattr(self.script.mtcs, "not_csc_comp") is False
            assert self.script.mtcs.check.mtptg is False


if __name__ == "__main__":
    unittest.main()
