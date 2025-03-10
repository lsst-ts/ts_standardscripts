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

from lsst.ts import salobj
from lsst.ts.idl.enums.Scheduler import SalIndex
from lsst.ts.standardscripts import get_scripts_dir
from lsst.ts.standardscripts.scheduler.stop import Stop
from lsst.ts.standardscripts.scheduler.testutils import BaseSchedulerTestCase


class TestSchedulerBaseStop(BaseSchedulerTestCase):
    async def basic_make_script(self, index):
        self.script = Stop(
            index=index,
            scheduler_index=SalIndex.MAIN_TEL,
        )
        return [self.script]

    async def test_no_stop_default(self) -> None:
        async with self.make_script(), self.make_controller(
            initial_state=salobj.State.ENABLED, publish_initial_state=True
        ):
            await self.configure_script()
            await self.run_script()

            assert len(self.controller.abort_observations) == 1
            assert not self.controller.abort_observations[0]

    async def test_no_stop_explicit(self) -> None:
        async with self.make_script(), self.make_controller(
            initial_state=salobj.State.ENABLED, publish_initial_state=True
        ):
            await self.configure_script(stop=False)
            await self.run_script()

            assert len(self.controller.abort_observations) == 1
            assert not self.controller.abort_observations[0]

    async def test_stop(self) -> None:
        async with self.make_script(), self.make_controller(
            initial_state=salobj.State.ENABLED, publish_initial_state=True
        ):
            await self.configure_script(stop=True)
            await self.run_script()

            assert len(self.controller.abort_observations) == 1
            assert self.controller.abort_observations[0]

    async def test_ocs_executable(self):
        scripts_dir = get_scripts_dir()
        script_path = scripts_dir / "ocs" / "scheduler" / "stop.py"
        await self.check_executable(script_path)
