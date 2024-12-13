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

import asyncio
import random
import types
import unittest

from lsst.ts import standardscripts
from lsst.ts.idl.enums.LaserTracker import LaserStatus
from lsst.ts.maintel.standardscripts.laser_tracker import AlignComponent, Measure
from lsst.ts.salobj import State

random.seed(47)  # for set_random_lsst_dds_partition_prefix


class TestMeasure(standardscripts.BaseScriptTestCase, unittest.IsolatedAsyncioTestCase):
    async def basic_make_script(self, index):
        self.script = Measure(index=index, add_remotes=False)
        self.script.mtcs = unittest.mock.AsyncMock()

        self.script.laser_tracker.rem.lasertracker_1 = unittest.mock.AsyncMock()
        self.script.laser_tracker.rem.lasertracker_1.configure_mock(
            **{
                "evt_offsetsPublish.next": self.get_offsets,
                "evt_laserStatus.aget": self.get_laser_status,
                "evt_summaryState.aget": self.get_summary_state,
                "evt_summaryState.next": self.get_summary_state,
            }
        )

        self.state_0 = [1, 2, 0, 0, 0]
        self.laser_status = types.SimpleNamespace(status=LaserStatus.ON)
        return (self.script,)

    async def get_summary_state(self, *args, **kwargs):
        return types.SimpleNamespace(summaryState=State.ENABLED)

    async def get_laser_status(self, *args, **kwags):
        await asyncio.sleep(0.5)
        return self.laser_status

    async def get_offsets(self, *args, **kwags):
        # return measured offsets
        await asyncio.sleep(0.5)
        self.offsets = types.SimpleNamespace(
            dX=1.0,
            dY=2.0,
            dZ=0.0,
            dRX=0.0,
            dRY=0.0,
        )

        return self.offsets

    async def test_configure(self):
        # Try configure with minimum set of parameters declared
        async with self.make_script():
            target = "M2"

            await self.configure_script(target=target)

            assert self.script.target == getattr(AlignComponent, target)

    async def test_run(self):
        # Start the test itself
        async with self.make_script():
            await self.configure_script(target="M2")

            # Run the script
            await self.run_script()

            assert self.state_0 == [1, 2, 0, 0, 0]

    async def test_executable(self):
        scripts_dir = standardscripts.get_scripts_dir()
        script_path = scripts_dir / "maintel" / "laser_tracker" / "measure.py"
        await self.check_executable(script_path)


if __name__ == "__main__":
    unittest.main()
