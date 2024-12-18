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

import pytest
from lsst.ts import salobj, standardscripts
from lsst.ts.idl.enums.Script import ScriptState
from lsst.ts.standardscripts.maintel.mtdome import SlewDome


class TestSlewDome(
    standardscripts.BaseScriptTestCase, unittest.IsolatedAsyncioTestCase
):
    async def basic_make_script(self, index):
        self.script = SlewDome(index=index)

        return (self.script,)

    @contextlib.asynccontextmanager
    async def make_dry_script(self):
        async with self.make_script(self):
            self.script.mtcs = unittest.mock.AsyncMock()
            self.script.mtcs.enable = unittest.mock.AsyncMock()
            self.script.mtcs.assert_all_enabled = unittest.mock.AsyncMock()
            self.script.mtcs.slew_dome_to = unittest.mock.AsyncMock()
            yield

    async def test_run(self):
        async with self.make_dry_script():
            await self.configure_script(az=0.0)

            await self.run_script()
            self.script.mtcs.enable.assert_awaited_once()
            self.script.mtcs.assert_all_enabled.assert_awaited_once()
            self.script.mtcs.slew_dome_to.assert_awaited_once()
            self.script.mtcs.slew_dome_to.assert_called_with(az=0.0)

    async def test_executable(self):
        scripts_dir = standardscripts.get_scripts_dir()
        script_path = scripts_dir / "maintel" / "mtdome" / "slew_dome.py"
        await self.check_executable(script_path)

    async def test_config(self):
        async with self.make_script():
            await self.configure_script(az=0.0)
            assert self.script.az == 0.0

    async def test_invalid_configurations(self):
        # Set of invalid configurations to test, all should fail to configure
        configs_bad = [dict(az="not_valid"), dict(az=[1, 3]), dict(az=None)]

        async with self.make_script():
            for config in configs_bad:
                with pytest.raises(salobj.ExpectedError):
                    await self.configure_script(**config)
                    assert self.script.state == ScriptState.CONFIGURE_FAILED

    async def test_configure_ignore(self):
        async with self.make_dry_script():
            components = ["mtptg"]
            await self.configure_script(az=0.0, ignore=components)

            self.script.mtcs.disable_checks_for_components.assert_called_once_with(
                components=components
            )


if __name__ == "__main__":
    unittest.main()
