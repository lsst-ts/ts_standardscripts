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

import asyncio
import logging
import random
import unittest

import pytest
from lsst.ts import salobj, standardscripts
from lsst.ts.auxtel.standardscripts import TakeImageLatiss, get_scripts_dir
from lsst.ts.xml.enums import Script

random.seed(47)  # for set_random_lsst_dds_partition_prefix

logging.basicConfig(level=logging.DEBUG)


class TestATCamTakeImage(
    standardscripts.BaseScriptTestCase, unittest.IsolatedAsyncioTestCase
):
    async def basic_make_script(self, index):
        self.script = TakeImageLatiss(index=index)
        self.atcam = salobj.Controller(name="ATCamera")
        self.atspec = salobj.Controller(name="ATSpectrograph")
        self.atheaderservice = salobj.Controller(name="ATHeaderService")

        self.nimages = 0
        self.image_index = 1
        self.selected_filter = []
        self.selected_disperser = []
        self.selected_linear_stage = []

        self.atcam.cmd_takeImages.callback = self.cmd_take_images_callback
        self.atspec.cmd_changeFilter.callback = self.cmd_changeFilter_callback
        self.atspec.cmd_changeDisperser.callback = self.cmd_changeDisperser_callback
        self.atspec.cmd_moveLinearStage.callback = self.cmd_moveLinearStage_callback

        self.end_image_tasks = []

        return self.atspec, self.atcam, self.atheaderservice, self.script

    async def close(self):
        """Optional cleanup before closing the scripts and etc."""
        await asyncio.gather(*self.end_image_tasks, return_exceptions=True)

    async def cmd_take_images_callback(self, data):
        one_exp_time = (
            data.expTime
            + self.script.camera.read_out_time
            + self.script.camera.shutter_time
        )
        image_name = f"AT_image_2020_{self.image_index:04d}"
        self.image_index += 1
        await self.atcam.evt_startIntegration.set_write(imageName=image_name)
        await asyncio.sleep(one_exp_time * data.numImages)
        self.nimages += 1
        self.end_image_tasks.append(
            asyncio.create_task(self.finish_take_images(image_name=image_name))
        )

    async def finish_take_images(self, image_name):
        await asyncio.sleep(0.5)
        await self.atcam.evt_endReadout.set_write(imageName=image_name)
        await asyncio.sleep(0.5)
        await self.atheaderservice.evt_largeFileObjectAvailable.write()

    async def cmd_changeFilter_callback(self, data):
        self.selected_filter.append(data.filter)
        await asyncio.sleep(0.5)

    async def cmd_changeDisperser_callback(self, data):
        self.selected_disperser.append(data.disperser)
        await asyncio.sleep(0.5)

    async def cmd_moveLinearStage_callback(self, data):
        self.selected_linear_stage.append(data.distanceFromHome)
        await asyncio.sleep(0.5)

    async def test_configure(self):
        async with self.make_script():
            exp_times = 1.1
            image_type = "OBJECT"
            await self.configure_script(exp_times=exp_times, image_type=image_type)
            assert self.script.config.exp_times == [exp_times]
            assert self.script.config.image_type == image_type
            assert self.script.config.filter is None
            assert self.script.config.grating is None
            assert self.script.config.linear_stage is None

        async with self.make_script():
            exp_times = 1.1
            image_type = "OBJECT"
            nimages = 2
            filter = None
            grating = None
            await self.configure_script(
                exp_times=exp_times,
                image_type=image_type,
                nimages=nimages,
                filter=filter,
                grating=grating,
            )
            assert self.script.config.exp_times == [exp_times, exp_times]
            assert self.script.config.image_type == image_type
            assert self.script.config.filter == filter
            assert self.script.config.grating == grating

        async with self.make_script():
            exp_times = 1.1
            nimages = 2
            filter = "blue"
            grating = 5
            linear_stage = 25
            await self.configure_script(
                exp_times=exp_times,
                image_type=image_type,
                nimages=nimages,
                filter=filter,
                grating=grating,
                linear_stage=linear_stage,
            )
            assert self.script.config.exp_times == [exp_times, exp_times]
            assert self.script.config.image_type == image_type
            assert self.script.config.filter == filter
            assert self.script.config.grating == grating
            assert self.script.config.linear_stage == linear_stage

        async with self.make_script():
            exp_times = [0, 2, 0.5]
            filter = 2
            grating = "a grating"
            await self.configure_script(
                exp_times=exp_times,
                image_type=image_type,
                filter=filter,
                grating=grating,
                linear_stage=linear_stage,
            )
            assert self.script.config.exp_times == exp_times
            assert self.script.config.image_type == image_type
            assert self.script.config.filter == filter
            assert self.script.config.grating == grating
            assert self.script.config.linear_stage == linear_stage

        async with self.make_script():
            exp_times = [0, 2, 0.5]
            nimages = len(exp_times) + 1
            with pytest.raises(salobj.ExpectedError):
                await self.configure_script(
                    exp_times=exp_times, image_type=image_type, nimages=nimages
                )

    async def run_take_images_test(
        self, mock_ready_to_take_data=None, expect_exception=None
    ):
        async with self.make_script():
            self.script.camera.ready_to_take_data = mock_ready_to_take_data

            config = await self.configure_script(
                nimages=1,
                exp_times=1.0,
                image_type="OBJECT",
                filter=1,
                grating=1,
                linear_stage=100,
            )

            if expect_exception is not None:
                await self.run_script(expected_final_state=Script.ScriptState.FAILED)
                self.assertEqual(self.script.state.state, Script.ScriptState.FAILED)
                self.assertIn(
                    str(mock_ready_to_take_data.side_effect), self.script.state.reason
                )

            else:
                await self.run_script()

            if mock_ready_to_take_data is not None:
                mock_ready_to_take_data.assert_called_once()
            else:
                with self.assertRaises(AttributeError):
                    self.script.camera.ready_to_take_data.assert_not_called()

            if expect_exception is None:
                assert self.nimages == config.nimages
                assert len(self.selected_filter) == config.nimages
                assert len(self.selected_disperser) == config.nimages
                assert len(self.selected_linear_stage) == config.nimages

                assert config.filter in self.selected_filter
                assert config.grating in self.selected_disperser
                assert config.linear_stage in self.selected_linear_stage

    async def test_take_images(self):
        await self.run_take_images_test()

    async def test_take_images_tcs_ready(self):
        mock_ready = unittest.mock.AsyncMock(return_value=None)
        await self.run_take_images_test(mock_ready_to_take_data=mock_ready)

    async def test_take_images_tcs_not_ready(self):
        mock_ready = unittest.mock.AsyncMock(side_effect=RuntimeError("TCS not ready"))
        await self.run_take_images_test(
            mock_ready_to_take_data=mock_ready, expect_exception=RuntimeError
        )

    async def test_executable(self):
        scripts_dir = get_scripts_dir()
        script_path = scripts_dir / "take_image_latiss.py"
        await self.check_executable(script_path)


if __name__ == "__main__":
    unittest.main()
