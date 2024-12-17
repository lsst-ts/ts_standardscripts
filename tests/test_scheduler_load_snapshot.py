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

import pytest
from lsst.ts import salobj
from lsst.ts.idl.enums.Scheduler import SalIndex
from lsst.ts.standardscripts import get_scripts_dir
from lsst.ts.standardscripts.scheduler.load_snapshot import LoadSnapshot
from lsst.ts.standardscripts.scheduler.testutils import BaseSchedulerTestCase


class TestSchedulerBaseLoadSnapshot(BaseSchedulerTestCase):
    async def basic_make_script(self, index):
        self.script = LoadSnapshot(
            index=index,
            scheduler_index=SalIndex.MAIN_TEL,
        )
        return [self.script]

    async def test_valid_uri(self) -> None:
        async with self.make_script(), self.make_controller(
            initial_state=salobj.State.ENABLED, publish_initial_state=True
        ):
            await self.configure_script(snapshot=self.controller.valid_snapshot)
            await self.run_script()

            self.assert_loaded_snapshots(snapshots=[self.controller.valid_snapshot])

    async def test_latest(self) -> None:
        async with self.make_script(), self.make_controller(
            initial_state=salobj.State.ENABLED, publish_initial_state=True
        ):
            await self.configure_script(snapshot="latest")
            await self.run_script()

            self.assert_loaded_snapshots(snapshots=[self.controller.valid_snapshot])

    async def test_invalid_uri(self) -> None:
        async with self.make_script(), self.make_controller(
            initial_state=salobj.State.ENABLED, publish_initial_state=True
        ):
            await self.configure_script(snapshot="invalid")

            with self.assertRaises(AssertionError):
                await self.run_script()

            self.assert_loaded_snapshots(snapshots=[])

    async def test_fail_config_latest_not_published(self) -> None:
        async with self.make_script(randomize_topic_subname=True), self.make_controller(
            initial_state=salobj.State.ENABLED, publish_initial_state=False
        ):
            with pytest.raises(salobj.ExpectedError):
                await self.configure_script(snapshot="latest")

    async def test_ocs_executable(self):
        scripts_dir = get_scripts_dir()
        script_path = scripts_dir / "ocs" / "scheduler" / "load_snapshot.py"
        await self.check_executable(script_path)
