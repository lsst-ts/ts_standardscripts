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

from lsst.ts import standardscripts
from lsst.ts.maintel.standardscripts.mtmount import ParkMount
from lsst.ts.xml.enums import MTMount


class TestParkMount(
    standardscripts.BaseScriptTestCase, unittest.IsolatedAsyncioTestCase
):
    async def basic_make_script(self, index):
        self.script = ParkMount(index=index)
        return (self.script,)

    @contextlib.asynccontextmanager
    async def make_dry_script(self):
        async with self.make_script(self):
            self.script.mtcs = unittest.mock.AsyncMock()
            self.script.mtcs.assert_all_enabled = unittest.mock.AsyncMock()
            self.script.mtcs.park_mount = unittest.mock.AsyncMock()
            yield

    async def test_executable(self):
        scripts_dir = standardscripts.get_scripts_dir()
        script_path = scripts_dir / "maintel" / "mtmount" / "park_mount.py"
        await self.check_executable(script_path)

    async def test_configure_ignore(self):
        async with self.make_script():
            components = ["mtptg"]
            await self.configure_script(position="ZENITH", ignore=components)
            assert self.script.mtcs.check.mtptg is False

    async def test_configure_ignore_not_mtcs_component(self):
        async with self.make_script():
            # Test the ignore feature with one non-MTCS component.
            components = ["not_mtcs_comp", "mtptg"]
            await self.configure_script(position="ZENITH", ignore=components)
            assert not hasattr(self.script.mtcs.check, "not_mtcs_comp")
            assert self.script.mtcs.check.mtptg is False

    async def test_park_zenith(self):
        async with self.make_dry_script():
            await self.configure_script(position="ZENITH")
            await self.run_script()
            self.script.mtcs.park_mount.assert_called_with(
                position=MTMount.ParkPosition.ZENITH
            )

    async def test_park_horizon(self):
        async with self.make_dry_script():
            await self.configure_script(position="HORIZON")
            await self.run_script()
            self.script.mtcs.park_mount.assert_called_with(
                position=MTMount.ParkPosition.HORIZON
            )
