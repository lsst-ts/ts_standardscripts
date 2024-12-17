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

from lsst.ts import salobj
from lsst.ts.idl.enums.Scheduler import SalIndex
from lsst.ts.idl.enums.Script import ScriptState
from lsst.ts.standardscripts import get_scripts_dir
from lsst.ts.standardscripts.scheduler import SetDesiredState
from lsst.ts.standardscripts.scheduler.testutils import BaseSchedulerTestCase


class TestSchedulerBaseStandBy(BaseSchedulerTestCase):
    async def basic_make_script(self, index):
        self.script = SetDesiredState(
            index=index,
            desired_state=salobj.State.STANDBY,
            descr="Send Scheduler to standby state",
            scheduler_index=SalIndex.MAIN_TEL,
        )
        return [self.script]

    async def test_run_csc_in_standby(self):
        """Set one remote to two states, including overrides."""
        async with self.make_script(), self.make_controller(
            initial_state=salobj.State.STANDBY, publish_initial_state=True
        ):
            await self.configure_script()
            await self.run_script()

            self.assert_run(
                expected_commands=dict(
                    standby=0,
                    start=0,
                    enable=0,
                    disable=0,
                ),
                expected_overrides=[],
                expected_script_state=ScriptState.DONE,
                expected_csc_state=salobj.State.STANDBY,
            )

    async def test_run_csc_in_standby_no_historical_data(self):
        """Set one remote to two states, including overrides."""
        async with self.make_script(randomize_topic_subname=True), self.make_controller(
            initial_state=salobj.State.STANDBY, publish_initial_state=False
        ):
            await self.configure_script()
            await self.run_script()

            self.assert_run(
                expected_commands=dict(
                    standby=1,
                    start=1,
                    enable=0,
                    disable=0,
                ),
                expected_overrides=[""],
                expected_script_state=ScriptState.DONE,
                expected_csc_state=salobj.State.STANDBY,
            )

    async def test_run_csc_in_disabled(self):
        """Set one remote to two states, including overrides."""
        async with self.make_script(), self.make_controller(
            initial_state=salobj.State.DISABLED, publish_initial_state=True
        ):
            await self.configure_script()
            await self.run_script()

            self.assert_run(
                expected_commands=dict(
                    standby=1,
                    start=0,
                    enable=0,
                    disable=0,
                ),
                expected_overrides=[],
                expected_script_state=ScriptState.DONE,
                expected_csc_state=salobj.State.STANDBY,
            )

    async def test_run_csc_in_disabled_no_historical_data(self):
        """Set one remote to two states, including overrides."""
        async with self.make_script(randomize_topic_subname=True), self.make_controller(
            initial_state=salobj.State.DISABLED, publish_initial_state=False
        ):
            await self.configure_script()
            await self.run_script()

            self.assert_run(
                expected_commands=dict(
                    standby=1,
                    start=0,
                    enable=0,
                    disable=0,
                ),
                expected_overrides=[],
                expected_script_state=ScriptState.DONE,
                expected_csc_state=salobj.State.STANDBY,
            )

    async def test_run_csc_in_enabled(self):
        """Set one remote to two states, including overrides."""
        async with self.make_script(), self.make_controller(
            initial_state=salobj.State.ENABLED, publish_initial_state=True
        ):
            await self.configure_script()
            await self.run_script()

            self.assert_run(
                expected_commands=dict(
                    standby=1,
                    start=0,
                    enable=0,
                    disable=1,
                ),
                expected_overrides=[],
                expected_script_state=ScriptState.DONE,
                expected_csc_state=salobj.State.STANDBY,
            )

    async def test_run_csc_in_enabled_no_historical_data(self):
        """Set one remote to two states, including overrides."""
        async with self.make_script(randomize_topic_subname=True), self.make_controller(
            initial_state=salobj.State.ENABLED, publish_initial_state=True
        ):
            await self.configure_script()
            await self.run_script()

            self.assert_run(
                expected_commands=dict(
                    standby=1,
                    start=0,
                    enable=0,
                    disable=1,
                ),
                expected_overrides=[],
                expected_script_state=ScriptState.DONE,
                expected_csc_state=salobj.State.STANDBY,
            )

    async def test_run_csc_in_fault(self):
        """Set one remote to two states, including overrides."""
        async with self.make_script(), self.make_controller(
            initial_state=salobj.State.FAULT, publish_initial_state=True
        ):
            await self.configure_script()
            await self.run_script()

            self.assert_run(
                expected_commands=dict(
                    standby=1,
                    start=0,
                    enable=0,
                    disable=0,
                ),
                expected_overrides=[],
                expected_script_state=ScriptState.DONE,
                expected_csc_state=salobj.State.STANDBY,
            )

    async def test_run_csc_in_fault_no_historical_data(self):
        """Set one remote to two states, including overrides."""
        async with self.make_script(randomize_topic_subname=True), self.make_controller(
            initial_state=salobj.State.FAULT, publish_initial_state=False
        ):
            await self.configure_script()
            await self.run_script()

            self.assert_run(
                expected_commands=dict(
                    standby=1,
                    start=0,
                    enable=0,
                    disable=0,
                ),
                expected_overrides=[],
                expected_script_state=ScriptState.DONE,
                expected_csc_state=salobj.State.STANDBY,
            )

    async def test_ocs_executable(self):
        scripts_dir = get_scripts_dir()
        script_path = scripts_dir / "ocs" / "scheduler" / "standby.py"
        await self.check_executable(script_path)


if __name__ == "__main__":
    unittest.main()
