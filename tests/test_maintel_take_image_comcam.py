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

import random
import unittest

import pytest
from lsst.ts import salobj, standardscripts
from lsst.ts.standardscripts.maintel import TakeImageComCam

random.seed(47)  # for set_random_lsst_dds_partition_prefix


class TestTakeImageComCam(
    standardscripts.BaseScriptTestCase, unittest.IsolatedAsyncioTestCase
):
    async def basic_make_script(self, index):
        self.script = TakeImageComCam(index=index)

        return (self.script,)

    async def test_configure_with_metadata_and_slew_time_sim(self):
        async with self.make_script():
            exp_times = 1.1
            image_type = "OBJECT"
            visit_metadata = dict(ra=10.0, dec=-90.0, rot_sky=5.0)
            slew_time = 10

            await self.configure_script(
                exp_times=exp_times,
                image_type=image_type,
                visit_metadata=visit_metadata,
                slew_time=slew_time,
                sim=True,
            )
            assert self.script.config.exp_times == [exp_times]
            assert self.script.config.image_type == image_type
            assert self.script.config.filter is None
            assert self.script.config.visit_metadata == visit_metadata
            assert self.script.config.slew_time == slew_time
            assert self.script.get_instrument_name() == "LSSTComCamSim"

    async def test_configure_no_filter(self):
        async with self.make_script():
            exp_times = 1.1
            image_type = "OBJECT"
            nimages = 2
            filter = None
            await self.configure_script(
                exp_times=exp_times,
                image_type=image_type,
                nimages=nimages,
                filter=filter,
            )
            assert self.script.config.exp_times == [exp_times, exp_times]
            assert self.script.config.image_type == image_type
            assert self.script.config.filter == filter

    async def test_configure_filter_as_str(self):
        async with self.make_script():
            exp_times = 1.1
            nimages = 2
            filter = "blue"
            image_type = "OBJECT"
            await self.configure_script(
                exp_times=exp_times,
                image_type=image_type,
                nimages=nimages,
                filter=filter,
            )
            assert self.script.config.exp_times == [exp_times, exp_times]
            assert self.script.config.image_type == image_type
            assert self.script.config.filter == filter

    async def test_configure_filter_as_number(self):
        async with self.make_script():
            exp_times = [0, 2, 0.5]
            filter = 2
            image_type = "OBJECT"
            await self.configure_script(
                exp_times=exp_times,
                image_type=image_type,
                filter=filter,
            )
            assert self.script.config.exp_times == exp_times
            assert self.script.config.image_type == image_type
            assert self.script.config.filter == filter

    async def test_configure_fails_missing_image_type(self):
        async with self.make_script():
            exp_times = [0, 2, 0.5]
            image_type = "OBJECT"
            nimages = len(exp_times) + 1
            with pytest.raises(salobj.ExpectedError):
                await self.configure_script(
                    exp_times=exp_times, image_type=image_type, nimages=nimages
                )

    async def test_take_images(self):
        async with self.make_script():
            self.script.camera.take_imgtype = unittest.mock.AsyncMock()
            self.script.camera.setup_instrument = unittest.mock.AsyncMock()

            nimages = 5

            await self.configure_script(
                nimages=nimages,
                exp_times=1.0,
                image_type="OBJECT",
                filter=1,
            )

            await self.run_script()

            assert nimages == self.script.camera.take_imgtype.await_count
            self.script.camera.setup_instrument.assert_awaited_once()
            self.script.camera.setup_instrument.assert_awaited_with(filter=1)

    async def test_executable_comcam(self):
        """Test that the script is executable for ComCam."""
        scripts_dir = standardscripts.get_scripts_dir()
        script_path = scripts_dir / "maintel" / "take_image_comcam.py"
        await self.check_executable(script_path)


if __name__ == "__main__":
    unittest.main()
