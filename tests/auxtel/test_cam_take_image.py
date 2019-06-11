# This file is part of ts_standardscripts
#
# Developed for the LSST Data Management System.
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
import unittest

import yaml

from lsst.ts import salobj

from lsst.ts.standardscripts.auxtel.atcam_take_image import ATCamTakeImage

index_gen = salobj.index_generator()

logging.basicConfig()


class Harness:
    def __init__(self):
        self.index = next(index_gen)
        salobj.test_utils.set_random_lsst_dds_domain()
        self.script = ATCamTakeImage(index=self.index)
        self.atcam = salobj.Controller(name="ATCamera")
        self.atspec = salobj.Controller(name="ATSpectrograph")

        self.nimages = 0
        self.selected_filter = []
        self.selected_disperser = []
        self.selected_linear_stage = []

        self.atcam.cmd_takeImages.callback = self.cmd_take_images_callback
        self.atspec.cmd_changeFilter.callback = self.cmd_changeFilter_callback
        self.atspec.cmd_changeDisperser.callback = self.cmd_changeDisperser_callback
        self.atspec.cmd_moveLinearStage.callback = self.cmd_moveLinearStage_callback

    async def cmd_take_images_callback(self, data):
        one_exp_time = data.expTime \
            + self.script.latiss.read_out_time + self.script.latiss.shutter_time
        await asyncio.sleep(one_exp_time*data.numImages)
        self.nimages += 1
        self.atcam.evt_endReadout.put()

    async def cmd_changeFilter_callback(self, data):
        self.selected_filter.append(data.filter)
        await asyncio.sleep(0.5)

    async def cmd_changeDisperser_callback(self, data):
        self.selected_disperser.append(data.disperser)
        await asyncio.sleep(0.5)

    async def cmd_moveLinearStage_callback(self, data):
        self.selected_linear_stage.append(data.distanceFromHome)
        await asyncio.sleep(0.5)

    async def __aenter__(self):
        await asyncio.gather(self.script.start_task,
                             self.atcam.start_task,
                             self.atspec.start_task)
        return self

    async def __aexit__(self, *args):
        await asyncio.gather(self.atspec.close(),
                             self.atcam.close(),
                             self.script.close())


class TestATCamTakeImage(unittest.TestCase):

    def test_exp_time_scalar_omit_nimages(self):
        async def doit():
            async with Harness() as harness:
                exp_time = 1.1
                config_kwargs = dict(exp_times=exp_time)
                config_data = harness.script.cmd_configure.DataType()
                config_data.config = yaml.safe_dump(config_kwargs)
                await harness.script.do_configure(data=config_data)
                await harness.script.do_run(data=None)
                self.assertEqual(harness.nimages, 1)
                self.assertEqual(harness.selected_filter, [])
                self.assertEqual(harness.selected_disperser, [])
                self.assertEqual(harness.selected_linear_stage, [])

        asyncio.get_event_loop().run_until_complete(doit())

    def test_exp_time_scalar_with_nimages(self):
        async def doit():
            async with Harness() as harness:
                exp_time = 1.1
                nimages = 2
                config_kwargs = dict(nimages=nimages, exp_times=exp_time)
                config_data = harness.script.cmd_configure.DataType()
                config_data.config = yaml.safe_dump(config_kwargs)
                await harness.script.do_configure(data=config_data)
                await harness.script.do_run(data=None)
                self.assertEqual(harness.nimages, nimages)
                self.assertEqual(harness.selected_filter, [])
                self.assertEqual(harness.selected_disperser, [])
                self.assertEqual(harness.selected_linear_stage, [])

        asyncio.get_event_loop().run_until_complete(doit())

    def test_exp_time_array_omit_nimages(self):
        async def doit():
            async with Harness() as harness:
                exp_times = [0, 2, 0.5]
                config_kwargs = dict(exp_times=exp_times)
                config_data = harness.script.cmd_configure.DataType()
                config_data.config = yaml.safe_dump(config_kwargs)
                await harness.script.do_configure(data=config_data)
                await harness.script.do_run(data=None)
                self.assertEqual(harness.nimages, len(exp_times))
                self.assertEqual(harness.selected_filter, [])
                self.assertEqual(harness.selected_disperser, [])
                self.assertEqual(harness.selected_linear_stage, [])

        asyncio.get_event_loop().run_until_complete(doit())

    def test_exp_time_array_with_matching_nimages(self):
        async def doit():
            async with Harness() as harness:
                exp_times = [0, 2, 0.5]
                nimages = len(exp_times)
                config_kwargs = dict(nimages=nimages, exp_times=exp_times)
                config_data = harness.script.cmd_configure.DataType()
                config_data.config = yaml.safe_dump(config_kwargs)
                await harness.script.do_configure(data=config_data)
                await harness.script.do_run(data=None)
                self.assertEqual(harness.nimages, len(exp_times))
                self.assertEqual(harness.selected_filter, [])
                self.assertEqual(harness.selected_disperser, [])
                self.assertEqual(harness.selected_linear_stage, [])

        asyncio.get_event_loop().run_until_complete(doit())

    def test_exp_time_array_with_mismatching_nimages(self):
        async def doit():
            async with Harness() as harness:
                exp_times = [0, 2, 0.5]
                nimages = len(exp_times) + 1
                config_kwargs = dict(nimages=nimages, exp_times=exp_times)
                config_data = harness.script.cmd_configure.DataType()
                config_data.config = yaml.safe_dump(config_kwargs)
                with self.assertRaises(salobj.ExpectedError):
                    await harness.script.do_configure(data=config_data)

        asyncio.get_event_loop().run_until_complete(doit())

    def test_take_images(self):
        async def doit():
            async with Harness() as harness:
                config_kwargs = dict(nimages=1,
                                     exp_times=0,
                                     filter=1,
                                     grating=1,
                                     linear_stage=100)
                config_data = harness.script.cmd_configure.DataType()
                config_data.config = yaml.safe_dump(config_kwargs)

                await harness.script.do_configure(data=config_data)
                await harness.script.do_run(data=None)

                self.assertEqual(harness.nimages, config_kwargs['nimages'])
                self.assertEqual(len(harness.selected_filter), config_kwargs['nimages'])
                self.assertEqual(len(harness.selected_disperser), config_kwargs['nimages'])
                self.assertEqual(len(harness.selected_linear_stage), config_kwargs['nimages'])

                self.assertIn(config_kwargs['filter'], harness.selected_filter)
                self.assertIn(config_kwargs['grating'], harness.selected_disperser)
                self.assertIn(config_kwargs['linear_stage'], harness.selected_linear_stage)

        asyncio.get_event_loop().run_until_complete(doit())


if __name__ == '__main__':
    unittest.main()
