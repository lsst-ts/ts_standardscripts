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
# along with this program.  If not, see <https://www.gnu.org/licenses/>.
import logging
import unittest

import pytest
from lsst.ts import salobj
from lsst.ts.idl.enums.Script import ScriptState
from lsst.ts.maintel.standardscripts import OffsetMTCS
from lsst.ts.standardscripts import BaseScriptTestCase, get_scripts_dir


class TestOffsetMTCS(BaseScriptTestCase, unittest.IsolatedAsyncioTestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.log = logging.getLogger(type(cls).__name__)

    async def basic_make_script(self, index):
        self.script = OffsetMTCS(index=index, add_remotes=False)

        return (self.script,)

    async def test_executable(self):
        scripts_dir = get_scripts_dir()
        script_path = scripts_dir / "maintel" / "offset_mtcs.py"
        self.log.debug(f"Checking for script in {script_path}")
        await self.check_executable(script_path)

    async def test_valid_configurations(self):
        # Set of valid configurations to test, considering different possible
        # combinations of configuration parameters
        configs_good = [
            dict(offset_azel=dict(az=180, el=60)),
            dict(offset_radec=dict(ra=15, dec=-30)),
            dict(offset_xy=dict(x=10, y=30)),
            dict(offset_rot=dict(rot=10)),
            dict(reset_offsets=dict(reset_absorbed=True, reset_non_absorbed=True)),
        ]

        self.remotes_needed = False
        async with self.make_script():
            for config in configs_good:
                await self.configure_script(**config)

                default_values = dict(
                    absorb=False,
                    relative=True,
                )

                self.assert_config(default_values, config)

    async def test_invalid_configurations(self):
        # Set of invalid configurations to test, all should fail to configure
        configs_bad = [
            dict(),
            dict(offset_xy=dict(x=0)),
            dict(offset_azel=dict(az=180)),
            dict(offset_radec=dict(ra=15)),
            dict(offset_xy=dict(x=10, y=30), offset_azel=dict(az=180, el=60)),
            dict(offset_xy=dict(x=10, y=30), reset_offsets=dict()),
        ]

        self.remotes_needed = False
        async with self.make_script():
            for config in configs_bad:
                with pytest.raises(salobj.ExpectedError):
                    await self.configure_script(**config)

                    assert self.state.state == ScriptState.CONFIGURE_FAILED

    def assert_config(self, default_values, config):
        configured_values = dict(
            offset_azel=self.script.offset_azel,
            offset_radec=self.script.offset_radec,
            offset_xy=self.script.offset_xy,
            offset_rot=self.script.offset_rot,
            reset_offsets=self.script.reset_offsets,
            absorb=self.script.absorb,
            relative=self.script.relative,
        )

        for parameter in default_values:
            with self.subTest(config=config, parameter=parameter):
                assert (
                    config.get(parameter, default_values.get(parameter))
                    == configured_values[parameter]
                )

    async def test_offset_azel(self):
        async with self.make_script():
            config = dict(offset_azel=dict(az=10, el=-10), absorb=False, relative=False)

            await self.configure_script(**config)

            self.script.mtcs.offset_azel = unittest.mock.AsyncMock()

            await self.run_script()

            self.script.mtcs.offset_azel.assert_awaited_once_with(
                az=10, el=-10, absorb=False, relative=False
            )

    async def test_offset_radec(self):
        async with self.make_script():
            config = dict(offset_radec=dict(ra=1, dec=-1))

            await self.configure_script(**config)

            self.script.mtcs.offset_radec = unittest.mock.AsyncMock()

            await self.run_script()

            self.script.mtcs.offset_radec.assert_awaited_once_with(
                ra=1,
                dec=-1,
            )

    async def test_offset_xy(self):
        async with self.make_script():
            config = dict(offset_xy=dict(x=10, y=-10))

            await self.configure_script(**config)

            self.script.mtcs.offset_xy = unittest.mock.AsyncMock()

            await self.run_script()

            self.script.mtcs.offset_xy.assert_awaited_once_with(
                x=10,
                y=-10,
                absorb=False,
                relative=True,
            )

    async def test_offset_rot(self):
        async with self.make_script():
            config = dict(offset_rot=dict(rot=10))

            await self.configure_script(**config)

            self.script.mtcs.offset_rot = unittest.mock.AsyncMock()

            await self.run_script()

            self.script.mtcs.offset_rot.assert_awaited_once_with(rot=10)

    async def test_reset_offsets(self):
        async with self.make_script():
            config = dict(
                reset_offsets=dict(reset_absorbed=True, reset_non_absorbed=True)
            )

            await self.configure_script(**config)

            self.script.mtcs.reset_offsets = unittest.mock.AsyncMock()

            await self.run_script()

            self.script.mtcs.reset_offsets.assert_awaited_once_with(
                absorbed=True,
                non_absorbed=True,
            )


if __name__ == "__main__":
    unittest.main()
