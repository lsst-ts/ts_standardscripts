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

import unittest

from lsst.ts import standardscripts
from lsst.ts.maintel.standardscripts.mtrotator import MoveRotator
from lsst.ts.observatory.control.maintel.mtcs import MTCS, MTCSUsages


class TestMoveRotator(
    standardscripts.BaseScriptTestCase, unittest.IsolatedAsyncioTestCase
):
    async def basic_make_script(self, index):
        self.script = MoveRotator(index=index)

        self.script.mtcs = MTCS(
            domain=self.script.domain,
            intended_usage=MTCSUsages.DryTest,
            log=self.script.log,
        )

        self.start_angle = 0.0  # degrees
        self.very_short_sleep = 0.1  # seconds
        self.script.mtcs.move_rotator = unittest.mock.AsyncMock()

        return (self.script,)

    async def test_configure_default(self):
        """Test the default configuration"""

        async with self.make_script():
            target_angle = 45.0

            await self.configure_script(angle=target_angle)

            assert self.script.target_angle == target_angle
            assert self.script.wait_for_complete is True
            assert self.script.program is None
            assert self.script.reason is None
            assert self.script.checkpoint_message is None

    async def test_configure_dont_wait_for_complete(self):
        """Test with the configuration where ``wait_for_complete`` is False"""

        async with self.make_script():
            target_angle = 45.0
            wait_for_complete = False

            await self.configure_script(angle=target_angle, wait_for_complete=False)

            assert self.script.target_angle == target_angle
            assert self.script.wait_for_complete is wait_for_complete
            assert self.script.program is None
            assert self.script.reason is None
            assert self.script.checkpoint_message is None

    @unittest.mock.patch(
        "lsst.ts.standardscripts.BaseBlockScript.obs_id", "202306060001"
    )
    async def test_configure_with_program_reason(self):
        """Testing a valid configuration: with program and reason"""

        # Try configure with a list of valid actuators ids
        async with self.make_script():
            self.script.get_obs_id = unittest.mock.AsyncMock(
                side_effect=["202306060001"]
            )
            await self.configure_script(
                angle=10.0,
                wait_for_complete=True,
                program="BLOCK-123",
                reason="SITCOM-321",
            )

            assert self.script.program == "BLOCK-123"
            assert self.script.reason == "SITCOM-321"
            assert (
                self.script.checkpoint_message
                == "MoveRotator BLOCK-123 202306060001 SITCOM-321"
            )

    async def test_run_with_default_config(self):
        async with self.make_script():
            target_angle = 45.0

            await self.configure_script(angle=target_angle)

            await self.run_script()

            self.script.mtcs.move_rotator.assert_called_once_with(
                position=target_angle, wait_for_in_position=True
            )

    async def test_executable(self):
        scripts_dir = standardscripts.get_scripts_dir()
        script_path = scripts_dir / "maintel" / "mtrotator" / "move_rotator.py"
        print(script_path)
        await self.check_executable(script_path)


if __name__ == "__main__":
    unittest.main()
