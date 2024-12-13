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
from lsst.ts.maintel.standardscripts.laser_tracker import Align, AlignComponent
from lsst.ts.observatory.control.maintel.mtcs import MTCS, MTCSUsages
from lsst.ts.observatory.control.remote_group import RemoteGroup, Usages
from lsst.ts.salobj import State

random.seed(47)  # for set_random_lsst_dds_partition_prefix


class TestAlign(standardscripts.BaseScriptTestCase, unittest.IsolatedAsyncioTestCase):
    async def basic_make_script(self, index):
        self.script = Align(index=index)
        self.script.laser_tracker = RemoteGroup(
            domain=self.script.domain,
            components=["LaserTracker:1"],
            intended_usage=Usages.DryTest,
            log=self.script.log,
        )

        self.script.mtcs = MTCS(
            domain=self.script.domain,
            intended_usage=MTCSUsages.DryTest,
            log=self.script.log,
        )

        self.script.mtcs = unittest.mock.AsyncMock()
        self.script.mtcs.configure_mock(
            **{
                "offset_m2_hexapod": self.apply_offsets,
                "offset_camera_hexapod": self.apply_offsets,
            }
        )

        self.script.laser_tracker.rem.lasertracker_1 = unittest.mock.AsyncMock()
        self.script.laser_tracker.rem.lasertracker_1.configure_mock(
            **{
                "evt_offsetsPublish.next": self.get_offsets,
                "evt_laserStatus.aget": self.get_laser_status,
                "evt_summaryState.aget": self.get_summary_state,
                "evt_summaryState.next": self.get_summary_state,
            }
        )

        self.state_0 = [1, 1, 1, 1, 1]
        self.laser_status = types.SimpleNamespace(status=LaserStatus.ON)
        return (self.script,)

    async def get_summary_state(self, *args, **kwargs):
        return types.SimpleNamespace(summaryState=State.ENABLED)

    async def get_laser_status(self, *args, **kwags):
        await asyncio.sleep(0.5)
        return self.laser_status

    async def apply_offsets(self, *args, **kwags):
        await asyncio.sleep(0.5)
        self.state_0 = [
            self.state_0[idx] + correction for idx, correction in enumerate(args)
        ]

    async def get_offsets(self, *args, **kwags):
        # return corrections to be non zero the first time this is called
        await asyncio.sleep(0.5)
        if any(self.state_0):
            offsets = types.SimpleNamespace(
                dX=0.5e-3,
                dY=0.5e-3,
                dZ=0.5e-3,
                dRX=0.5,
                dRY=0.5,
            )
        else:
            offsets = types.SimpleNamespace(
                dX=0.0,
                dY=0.0,
                dZ=0.0,
                dRX=0.0,
                dRY=0.0,
            )

        return offsets

    async def test_configure(self):
        # Try configure with minimum set of parameters declared
        async with self.make_script():
            max_iter = 10
            target = "M2"
            tolerance_linear = 1.0e-7
            tolerance_angular = 5.0 / 3600.0

            await self.configure_script(
                max_iter=max_iter,
                target=target,
                tolerance_linear=tolerance_linear,
                tolerance_angular=tolerance_angular,
            )

            assert self.script.max_iter == max_iter
            assert self.script.target == getattr(AlignComponent, target)
            assert self.script.tolerance_linear == tolerance_linear
            assert self.script.tolerance_angular == tolerance_angular

    async def test_run(self):
        # Start the test itself
        async with self.make_script():
            await self.configure_script(
                max_iter=10,
                target="M2",
                tolerance_angular=5.0 / 3600.0,
            )

            # Run the script
            await self.run_script()

            assert self.state_0 == [0, 0, 0, 0, 0]

    async def test_executable(self):
        scripts_dir = standardscripts.get_scripts_dir()
        script_path = scripts_dir / "maintel" / "laser_tracker" / "align.py"
        await self.check_executable(script_path)


if __name__ == "__main__":
    unittest.main()
