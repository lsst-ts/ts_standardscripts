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
from lsst.ts.observatory.control.maintel.comcam import ComCam, ComCamUsages
from lsst.ts.observatory.control.maintel.mtcs import MTCS, MTCSUsages
from lsst.ts.standardscripts.maintel import Mode, TakeAOSSequenceComCam


class TestTakeAOSSequenceComCam(
    standardscripts.BaseScriptTestCase, unittest.IsolatedAsyncioTestCase
):
    async def basic_make_script(self, index):
        self.script = TakeAOSSequenceComCam(index=index)

        self.script.mtcs = MTCS(
            domain=self.script.domain,
            intended_usage=MTCSUsages.DryTest,
            log=self.script.log,
        )

        self.script.camera = ComCam(
            domain=self.script.domain,
            intended_usage=ComCamUsages.DryTest,
            log=self.script.log,
        )

        self.script.mtcs.offset_camera_hexapod = unittest.mock.AsyncMock()
        self.script.camera.take_cwfs = unittest.mock.AsyncMock()
        self.script.camera.take_acq = unittest.mock.AsyncMock()

        return (self.script,)

    async def test_configure(self):
        async with self.make_script():
            exposure_time = 15.0
            filter = "g"
            dz = 2000.0
            n_sequences = 15
            mode = "INTRA"

            await self.configure_script(
                filter=filter,
                exposure_time=exposure_time,
                dz=dz,
                n_sequences=n_sequences,
                mode=mode,
            )
            assert self.script.exposure_time == exposure_time
            assert self.script.filter == filter
            assert self.script.dz == 2000.0
            assert self.script.n_sequences == n_sequences
            assert self.script.mode == Mode.INTRA

    async def test_configure_ignore(self):
        async with self.make_script():
            self.script.mtcs.check.mtmount = True
            self.script.mtcs.check.mtrotator = True
            self.script.mtcs.check.mtm2 = True
            self.script.camera.check.ccoods = True

            exposure_time = 15.0
            filter = "g"
            dz = 2000.0
            n_sequences = 15
            mode = "INTRA"
            ignore = ["mtrotator", "mtm2", "ccoods"]

            await self.configure_script(
                filter=filter,
                exposure_time=exposure_time,
                dz=dz,
                n_sequences=n_sequences,
                ignore=ignore,
                mode=mode,
            )
            assert self.script.exposure_time == exposure_time
            assert self.script.filter == filter
            assert self.script.dz == 2000.0
            assert self.script.n_sequences == n_sequences
            assert self.script.mode == Mode.INTRA
            assert self.script.mtcs.check.mtmount
            assert not self.script.mtcs.check.mtrotator
            assert not self.script.mtcs.check.mtm2
            assert not self.script.camera.check.ccoods

    async def test_take_triplets(self):
        async with self.make_script():
            exposure_time = 15.0
            filter = "g"
            dz = 2000.0
            n_sequences = 3
            mode = "TRIPLET"

            await self.configure_script(
                filter=filter,
                exposure_time=exposure_time,
                dz=dz,
                n_sequences=n_sequences,
                mode=mode,
            )

            await self.run_script()

            assert n_sequences * 2 == self.script.camera.take_cwfs.await_count
            assert n_sequences == self.script.camera.take_acq.await_count

    async def test_take_doublet(self):
        async with self.make_script():
            exposure_time = 15.0
            filter = "g"
            dz = 2000.0
            n_sequences = 3
            mode = "INTRA"

            await self.configure_script(
                filter=filter,
                exposure_time=exposure_time,
                dz=dz,
                n_sequences=n_sequences,
                mode=mode,
            )

            await self.run_script()

            assert n_sequences == self.script.camera.take_cwfs.await_count
            assert n_sequences == self.script.camera.take_acq.await_count

    async def test_executable_lsstcam(self) -> None:
        """Test that the script is executable."""
        scripts_dir = standardscripts.get_scripts_dir()
        script_path = scripts_dir / "maintel" / "take_aos_sequence_comcam.py"
        await self.check_executable(script_path)


if __name__ == "__main__":
    unittest.main()
