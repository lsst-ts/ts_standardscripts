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

from lsst.ts.idl.enums.ScriptQueue import SalIndex
from lsst.ts.standardscripts import BaseScriptTestCase, get_scripts_dir
from lsst.ts.standardscripts.pause_queue import PauseQueue


class TestPauseQueue(BaseScriptTestCase, unittest.IsolatedAsyncioTestCase):
    async def basic_make_script(self, index):
        self.script = PauseQueue(index=index)

        # Mock the script queue and its pause method
        self.script.script_queue = unittest.mock.MagicMock()
        self.script.script_queue.pause = unittest.mock.AsyncMock(return_value=None)

        return (self.script,)

    async def test_configure(self):
        async with self.make_script():
            queue = "MAIN_TEL"
            expected_queue_index = SalIndex.MAIN_TEL

            config = types.SimpleNamespace(queue=queue)
            await self.script.configure(config)

            assert self.script.queue_index == expected_queue_index

    async def test_run(self):
        """
        Test that the script is paused for the selected queue.
        """
        async with self.make_script():
            # Configure the script
            queue = "MAIN_TEL"
            await self.configure_script(queue=queue)

            # Run the script
            await self.run_script()

            self.script.script_queue.pause.assert_awaited_once()

    async def test_executable(self):
        scripts_dir = get_scripts_dir()
        script_path = scripts_dir / "pause_queue.py"
        await self.check_executable(script_path)


if __name__ == "__main__":
    unittest.main()
