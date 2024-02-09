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

import types
import unittest

from lsst.ts.standardscripts import BaseScriptTestCase, get_scripts_dir
from lsst.ts.standardscripts.mute_alarms import MuteAlarms
from lsst.ts.xml.enums.Watcher import AlarmSeverity


class TestMuteAlarms(BaseScriptTestCase, unittest.IsolatedAsyncioTestCase):
    async def basic_make_script(self, index):
        self.script = MuteAlarms(index=index)
        self.script.watcher = unittest.mock.AsyncMock()
        return (self.script,)

    async def test_configure(self):
        async with self.make_script():
            config = types.SimpleNamespace(
                name=".*",
                mutedBy="test",
                duration=10,
                severity="WARNING",
            )
            await self.script.configure(config)
            pass

    async def test_run(self):
        """
        Test that the script is paused for the selected queue.
        """
        async with self.make_script():
            config = types.SimpleNamespace(
                name=".*",
                mutedBy="test",
                duration=10,
                severity="WARNING",
            )

            # Configure the script
            await self.configure_script(
                name=config.name,
                mutedBy=config.mutedBy,
                duration=config.duration,
                severity=config.severity,
            )

            # Run the script
            await self.run_script()

            # Assert the command was called properly
            self.script.watcher.cmd_mute.set_start.assert_awaited_with(
                name=config.name,
                duration=config.duration,
                severity=AlarmSeverity[config.severity],
                mutedBy=config.mutedBy,
                timeout=self.script.std_timeout,
            )

    async def test_executable(self):
        scripts_dir = get_scripts_dir()
        script_path = scripts_dir / "pause_queue.py"
        await self.check_executable(script_path)


if __name__ == "__main__":
    unittest.main()
