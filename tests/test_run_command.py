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

import random
import unittest

import pytest
from lsst.ts import salobj, standardscripts

random.seed(47)  # for set_random_lsst_dds_partition_prefix


class TestRunCommand(
    standardscripts.BaseScriptTestCase, unittest.IsolatedAsyncioTestCase
):
    async def basic_make_script(self, index):
        self.script = standardscripts.RunCommand(index=index)
        self.controller = salobj.Controller("Test", index=1)
        self.controller.cmd_setScalars.callback = self.set_scalars_callback
        return [self.script, self.controller]

    async def set_scalars_callback(self, data):
        await self.controller.evt_scalars.set_write(
            float0=data.float0, string0=data.string0
        )

    async def test_configure_errors(self):
        """Test error handling in the do_configure method."""
        for bad_config in (
            {},  # need component name and command name
            {"component": "Test:1"},  # need command name
            {"cmd": "setScalars"},  # need component name
        ):
            with self.subTest(bad_config=bad_config):
                async with self.make_script():
                    with pytest.raises(salobj.ExpectedError):
                        await self.configure_script(**bad_config)

    async def test_configure_good(self):
        """Test the configure method with a valid configuration."""
        async with self.make_script():
            # Basic providing only component and command
            await self.configure_script(component="Test:1", cmd="setScalars")

            assert self.script.name == "Test"
            assert self.script.index == 1
            assert self.script.cmd == "setScalars"
            assert self.script.event is None
            assert not self.script.flush

        async with self.make_script():
            # Provide event
            await self.configure_script(
                component="Test:1", cmd="setScalars", event="scalars"
            )

            assert self.script.name == "Test"
            assert self.script.index == 1
            assert self.script.cmd == "setScalars"
            assert self.script.event == "scalars"
            assert self.script.flush

        async with self.make_script():
            # Provide event with flush = False
            await self.configure_script(
                component="Test:1", cmd="setScalars", event="scalars", flush=False
            )

            assert self.script.name == "Test"
            assert self.script.index == 1
            assert self.script.cmd == "setScalars"
            assert self.script.event == "scalars"
            assert not self.script.flush

        async with self.make_script():
            # Provide parameter for the command
            await self.configure_script(
                component="Test:1",
                cmd="setScalars",
                event="scalars",
                parameters={"float0": 1.2345, "string0": "12345"},
            )

            assert self.script.name == "Test"
            assert self.script.index == 1
            assert self.script.cmd == "setScalars"
            assert self.script.event == "scalars"
            assert self.script.flush
            assert self.script.remote.cmd_setScalars.data.float0 == pytest.approx(
                1.2345, abs=0.00005
            )
            assert self.script.remote.cmd_setScalars.data.string0 == "12345"

    async def test_run(self):
        """Run test with Test component."""

        async with self.make_script():
            # Provide parameter for the command
            await self.configure_script(
                component="Test:1",
                cmd="setScalars",
                event="scalars",
                parameters={"float0": 1.2345, "string0": "12345"},
            )

            await self.run_script()

            assert self.controller.evt_scalars.data.float0 == pytest.approx(
                1.2345, abs=0.00005
            )
            assert self.controller.evt_scalars.data.string0 == "12345"

    async def test_executable(self):
        scripts_dir = standardscripts.get_scripts_dir()
        script_path = scripts_dir / "set_summary_state.py"
        await self.check_executable(script_path)


if __name__ == "__main__":
    unittest.main()
