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

import random
import unittest.mock

from lsst.ts import salobj, utils
from lsst.ts.idl.enums import Script
from lsst.ts.maintel.standardscripts import SetupMTCS, get_scripts_dir
from lsst.ts.standardscripts import BaseScriptTestCase

random.seed(47)  # for set_random_lsst_dds_partition_prefix

index_gen = utils.index_generator()


class TestSetupMTCS(BaseScriptTestCase, unittest.IsolatedAsyncioTestCase):
    async def basic_make_script(self, index):
        self.script = SetupMTCS(index=index, remotes=False)
        self.script.checkpoints_activities = [
            (checkpoint, unittest.mock.AsyncMock())
            for checkpoint, _ in self.script.checkpoints_activities
        ]
        return (self.script,)

    async def test_configure_errors(self):
        """Test error handling in the do_configure method."""
        # Check schema validation.
        for bad_config in (
            # The only *bad* case is that ccw_following has invalid value
            {"ccw_following": "BADVALUE"},
        ):
            with self.subTest(bad_config=bad_config):
                async with self.make_script():
                    with self.assertRaises(salobj.ExpectedError):
                        await self.configure_script(**bad_config)

    async def test_configure_good(self):
        """Test configure method with valid configurations."""
        async with self.make_script():
            # Start with default configuration
            await self.configure_script()

            # The default value for `ccw_following` is True
            self.assertEqual(self.script.config.ccw_following, True)

        async with self.make_script():
            # Now try to change that to False
            ccw_following = False
            await self.configure_script(
                ccw_following=ccw_following,
            )

            # Check configuration was correctly loaded
            self.assertEqual(self.script.config.ccw_following, ccw_following)

    async def test_executable(self):
        scripts_dir = get_scripts_dir()
        script_path = scripts_dir / "setup_mtcs.py"
        await self.check_executable(script_path)

    async def test_run(self):
        # Start the test itself
        async with self.make_script():
            # Configure the script
            await self.configure_script()
            assert self.script.state.state == Script.ScriptState.CONFIGURED

            # Run the script
            await self.run_script()
            assert self.script.state.state == Script.ScriptState.DONE

            # Check that runs the activities only once
            for checkpoint, activity in self.script.checkpoints_activities:
                activity.assert_awaited_once()


if __name__ == "__main__":
    unittest.main()
