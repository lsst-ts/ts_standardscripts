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

import asyncio
import logging
import random
import unittest

from lsst.ts import salobj
from lsst.ts import standardscripts
from lsst.ts.standardscripts.auxtel import TakeImageLatiss

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
        await asyncio.sleep(one_exp_time * data.numImages)
        self.nimages += 1
        self.end_image_tasks.append(asyncio.create_task(self.finish_take_images()))

    async def finish_take_images(self):
        await asyncio.sleep(0.5)
        self.atcam.evt_endReadout.set_put(imageName="AT_image_2020_001")
        await asyncio.sleep(0.5)
        self.atheaderservice.evt_largeFileObjectAvailable.put()

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
            self.assertEqual(self.script.config.exp_times, [exp_times])
            self.assertEqual(self.script.config.image_type, image_type)
            self.assertIsNone(self.script.config.filter)
            self.assertIsNone(self.script.config.grating)
            self.assertIsNone(self.script.config.linear_stage)

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
            self.assertEqual(self.script.config.exp_times, [exp_times, exp_times])
            self.assertEqual(self.script.config.image_type, image_type)
            self.assertEqual(self.script.config.filter, filter)
            self.assertEqual(self.script.config.grating, grating)

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
            self.assertEqual(self.script.config.exp_times, [exp_times, exp_times])
            self.assertEqual(self.script.config.image_type, image_type)
            self.assertEqual(self.script.config.filter, filter)
            self.assertEqual(self.script.config.grating, grating)
            self.assertEqual(self.script.config.linear_stage, linear_stage)

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
            self.assertEqual(self.script.config.exp_times, exp_times)
            self.assertEqual(self.script.config.image_type, image_type)
            self.assertEqual(self.script.config.filter, filter)
            self.assertEqual(self.script.config.grating, grating)
            self.assertEqual(self.script.config.linear_stage, linear_stage)

            exp_times = [0, 2, 0.5]
            nimages = len(exp_times) + 1
            with self.assertRaises(salobj.ExpectedError):
                await self.configure_script(
                    exp_times=exp_times, image_type=image_type, nimages=nimages
                )

    async def test_take_images(self):
        async with self.make_script():
            config = await self.configure_script(
                nimages=1,
                exp_times=1.0,
                image_type="OBJECT",
                filter=1,
                grating=1,
                linear_stage=100,
            )
            await self.run_script()

            self.assertEqual(self.nimages, config.nimages)
            self.assertEqual(len(self.selected_filter), config.nimages)
            self.assertEqual(len(self.selected_disperser), config.nimages)
            self.assertEqual(len(self.selected_linear_stage), config.nimages)

            self.assertIn(config.filter, self.selected_filter)
            self.assertIn(config.grating, self.selected_disperser)
            self.assertIn(config.linear_stage, self.selected_linear_stage)

    async def test_executable(self):
        scripts_dir = standardscripts.get_scripts_dir()
        script_path = scripts_dir / "auxtel" / "take_image_latiss.py"
        await self.check_executable(script_path)


if __name__ == "__main__":
    unittest.main()
