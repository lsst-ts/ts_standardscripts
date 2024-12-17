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

from lsst.ts.idl.enums.Scheduler import SalIndex
from lsst.ts.maintel.standardscripts import get_scripts_dir
from lsst.ts.standardscripts.scheduler.load_snapshot import LoadSnapshot
from lsst.ts.standardscripts.scheduler.testutils import BaseSchedulerTestCase


class TestSchedulerBaseLoadSnapshot(BaseSchedulerTestCase):
    async def basic_make_script(self, index):
        self.script = LoadSnapshot(
            index=index,
            scheduler_index=SalIndex.MAIN_TEL,
        )
        return [self.script]

    async def test_executable(self):
        scripts_dir = get_scripts_dir()
        script_path = scripts_dir / "scheduler" / "load_snapshot.py"
        await self.check_executable(script_path)
