# This file is part of ts_auxtel_standardscripts
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
import unittest

from lsst.ts import salobj, standardscripts
from lsst.ts.auxtel.standardscripts import TakeStutteredLatiss, get_scripts_dir
from lsst.ts.observatory.control.mock import LATISSMock

random.seed(47)  # for set_random_lsst_dds_partition_prefix


class TestATCamTakeImage(
    standardscripts.BaseScriptTestCase, unittest.IsolatedAsyncioTestCase
):
    async def basic_make_script(self, index):
        self.script = TakeStutteredLatiss(index=index)

        self.latiss_mock = LATISSMock()

        return self.latiss_mock, self.script

    async def test_configure_good_minimum(self):
        async with self.make_script():
            config = await self.configure_script(
                exp_time=1.0,
            )

            assert self.script.config.exp_time == config.exp_time
            assert self.script.config.n_images == 1
            assert self.script.config.n_shift == 20
            assert self.script.config.row_shift == 100
            assert self.script.config.filter is None
            assert self.script.config.grating is None
            assert self.script.config.linear_stage is None
            assert not hasattr(self.script.config, "reason")
            assert not hasattr(self.script.config, "program")
            assert not hasattr(self.script.config, "note")

    async def test_configure_good_all(self):
        async with self.make_script():
            config = await self.configure_script(
                exp_time=1.1,
                n_images=2,
                n_shift=10,
                row_shift=50,
                filter="SDSSr",
                grating="FEH660",
                linear_stage=10.0,
                reason="Test",
                program="UNIT_TEST",
                note="something_important",
            )

            assert self.script.config.exp_time == config.exp_time
            assert self.script.config.n_images == config.n_images
            assert self.script.config.n_shift == config.n_shift
            assert self.script.config.row_shift == config.row_shift
            assert self.script.config.filter == config.filter
            assert self.script.config.grating == config.grating
            assert self.script.config.linear_stage == config.linear_stage
            assert self.script.config.reason == config.reason
            assert self.script.config.program == config.program
            assert self.script.config.note == config.note

    async def test_configure_bad(self):
        for bad_config in (
            dict(),  # no config
            dict(n_images=0),
            dict(n_shift=0),
            dict(row_shift=0),
            dict(exptime=-1.0),
        ):
            with self.subTest(bad_config=bad_config):
                async with self.make_script():
                    with self.assertRaises(salobj.ExpectedError):
                        await self.configure_script(**bad_config)

    async def test_run(self):
        async with self.make_script():
            await self.configure_script(
                exp_time=1.0,
            )

            await self.run_script()

            assert self.latiss_mock.nimages == self.script.config.n_images

    async def test_executable(self):
        scripts_dir = get_scripts_dir()
        script_path = scripts_dir / "take_stuttered_latiss.py"
        await self.check_executable(script_path)


if __name__ == "__main__":
    unittest.main()
