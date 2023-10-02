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
import contextlib
import logging
import unittest

import pytest
from lsst.ts import salobj
from lsst.ts.idl.enums.Script import ScriptState
from lsst.ts.standardscripts import BaseScriptTestCase, get_scripts_dir
from lsst.ts.standardscripts.maintel import OffsetCameraHexapod


class TestOffsetCameraHexapod(BaseScriptTestCase, unittest.IsolatedAsyncioTestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.log = logging.getLogger(type(cls).__name__)

    async def basic_make_script(self, index):
        self.script = OffsetCameraHexapod(index=index, add_remotes=False)

        return (self.script,)

    @contextlib.asynccontextmanager
    async def setup_mocks(self):
        self.script.mtcs.offset_camera_hexapod = unittest.mock.AsyncMock()
        yield

    async def test_executable(self):
        scripts_dir = get_scripts_dir()
        script_path = scripts_dir / "maintel" / "offset_camera_hexapod.py"
        self.log.debug(f"Checking for script in {script_path}")
        await self.check_executable(script_path)

    async def test_valid_configurations(self):
        # Set of valid configurations to test, considering different possible
        # combinations of configuration parameters
        configs_good = [
            dict(z=0.1),
            dict(x=0.1, y=0.2),
            dict(x=0.1, u=0.1, v=-0.1, sync=False),
        ]

        self.remotes_needed = False
        async with self.make_script():
            for config in configs_good:
                await self.configure_script(**config)

                default_values = dict(
                    x=0,
                    y=0,
                    z=0,
                    u=0,
                    v=0,
                    sync=True,
                )

                self.assert_config(default_values, config)

    async def test_invalid_configurations(self):
        # Set of invalid configurations to test, all should fail to configure
        configs_bad = [
            dict(),
        ]

        self.remotes_needed = False
        async with self.make_script():
            for config in configs_bad:
                with pytest.raises(salobj.ExpectedError):
                    await self.configure_script(**config)

                    assert self.state.state == ScriptState.CONFIGURE_FAILED

    def assert_config(self, default_values, config):
        configured_values = dict(
            x=self.script.offsets["x"],
            y=self.script.offsets["y"],
            z=self.script.offsets["z"],
            u=self.script.offsets["u"],
            v=self.script.offsets["v"],
            sync=self.script.sync,
        )

        for parameter in default_values:
            with self.subTest(config=config, parameter=parameter):
                assert (
                    config.get(parameter, default_values.get(parameter))
                    == configured_values[parameter]
                )

    async def test_offset_camera_hexapod(self):
        async with self.make_script(), self.setup_mocks():
            config = dict(x=-0.1, y=0.2, z=0.1, u=-1.0, v=1.0, sync=False)

            await self.configure_script(**config)

            await self.run_script()

            self.script.mtcs.offset_camera_hexapod.assert_awaited_once_with(
                x=-0.1, y=0.2, z=0.1, u=-1.0, v=1.0, sync=False
            )


if __name__ == "__main__":
    unittest.main()
