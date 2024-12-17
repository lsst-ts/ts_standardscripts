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

import asyncio
import random
import types
import unittest

import numpy as np
import yaml
from lsst.ts import standardscripts
from lsst.ts.maintel.standardscripts import CloseLoopLSSTCam, get_scripts_dir
from lsst.ts.observatory.control.maintel.lsstcam import LSSTCam, LSSTCamUsages
from lsst.ts.observatory.control.maintel.mtcs import MTCS, MTCSUsages
from lsst.ts.observatory.control.utils.enums import ClosedLoopMode

random.seed(47)  # for set_random_lsst_dds_partition_prefix


class TestCloseLoopLSSTCam(
    standardscripts.BaseScriptTestCase, unittest.IsolatedAsyncioTestCase
):
    async def basic_make_script(self, index):
        self.script = CloseLoopLSSTCam(index=index)

        self.script.mtcs = MTCS(
            domain=self.script.domain,
            intended_usage=MTCSUsages.DryTest,
            log=self.script.log,
        )

        self.script._camera = LSSTCam(
            domain=self.script.domain,
            intended_usage=LSSTCamUsages.DryTest,
            log=self.script.log,
        )

        # MTCS mocks
        self.script.mtcs.assert_all_enabled = unittest.mock.AsyncMock()
        self.script.mtcs.offset_camera_hexapod = unittest.mock.AsyncMock()
        self.script.mtcs.rem.mtrotator = unittest.mock.AsyncMock()
        self.script.mtcs.rem.mtrotator.configure_mock(
            **{
                "tel_rotation.next.return_value": types.SimpleNamespace(
                    actualPosition=0.0
                ),
            }
        )

        # MTAOS mocks
        self.script.mtcs.rem.mtaos = unittest.mock.AsyncMock()
        self.script.mtcs.rem.mtaos.configure_mock(
            **{
                "cmd_runWEP.set_start": unittest.mock.AsyncMock(),
                "cmd_runOFC.set_start": self.get_offsets,
                "evt_wavefrontError.next": self.return_zernikes,
                "evt_degreeOfFreedom.next": self.return_offsets,
                "cmd_issueCorrection.start": self.apply_offsets,
                "evt_wavefrontError.flush": unittest.mock.AsyncMock(),
            }
        )

        # Camera mocks
        self.script.camera.assert_all_enabled = unittest.mock.AsyncMock()
        self.script.camera.take_acq = unittest.mock.AsyncMock()
        self.script.camera.take_cwfs = unittest.mock.AsyncMock()

        self.script.assert_mode_compatibility = unittest.mock.AsyncMock()

        self.state_0 = np.zeros(50)
        self.state_0[:5] += 1

        self.corrections = types.SimpleNamespace(visitDoF=np.zeros(50))

        return (self.script,)

    async def return_zernikes(self, *args, **kwargs):
        return np.random.rand(19)

    async def return_offsets(self, *args, **kwargs):
        return self.corrections

    async def apply_offsets(self, *args, **kwags):
        await asyncio.sleep(0.5)
        self.state_0 += self.corrections.visitDoF

    async def get_offsets(self, *args, **kwags):
        # return corrections to be non zero the first time this is called
        await asyncio.sleep(0.5)
        self.corrections = types.SimpleNamespace(visitDoF=np.zeros(50))

        if any(self.state_0):
            self.corrections.visitDoF[:5] -= 0.5

    async def test_configure(self):
        # Try configure with minimum set of parameters declared
        async with self.make_script():
            mode = "CWFS"
            max_iter = 10
            exposure_time = 30
            filter = "r"
            used_dofs = ["M2_dz", "M2_dx", "M2_dy", "M2_rx", "M2_ry"]
            threshold = [0.005] * 50
            apply_corrections = True

            await self.configure_script(
                mode=mode,
                max_iter=max_iter,
                exposure_time=exposure_time,
                filter=filter,
                used_dofs=used_dofs,
                threshold=threshold,
                apply_corrections=apply_corrections,
            )

            assert self.script.mode == ClosedLoopMode.CWFS
            assert self.script.max_iter == max_iter
            assert self.script.exposure_time == exposure_time
            assert self.script.filter == filter

            configured_dofs = np.zeros(50)
            configured_dofs[:5] += 1
            assert all(self.script.used_dofs == configured_dofs)
            assert self.script.threshold == threshold
            assert self.script.apply_corrections == apply_corrections

    async def test_configure_wep_config(self):
        async with self.make_script():
            wep_config_dic = {"field1": "val1", "field2": "val2"}
            await self.configure_script(wep_config=wep_config_dic, filter="r")
            assert self.script.wep_config == yaml.dump(wep_config_dic)

    async def test_run(self):
        # Start the test itself
        async with self.make_script():
            await self.configure_script(
                max_iter=10,
                filter="r",
                used_dofs=[0, 1, 2, 3, 4],
            )

            # Run the script
            await self.run_script()

            assert all(self.state_0 == np.zeros(50))

    async def test_executable_close_loop_lsstcam(self) -> None:
        """Test that the script is executable for LSSTCam."""
        scripts_dir = get_scripts_dir()
        script_path = scripts_dir / "close_loop_lsstcam.py"
        await self.check_executable(script_path)

    async def test_executable_close_loop_comcam(self) -> None:
        """Test that the script is executable for ComCam."""
        scripts_dir = get_scripts_dir()
        script_path = scripts_dir / "close_loop_comcam.py"
        await self.check_executable(script_path)


if __name__ == "__main__":
    unittest.main()
