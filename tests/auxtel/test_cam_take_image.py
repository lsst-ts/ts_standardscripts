import unittest
import asyncio

import yaml

from lsst.ts import salobj

from lsst.ts.standardscripts.auxtel.atcam_take_image import ATCamTakeImage

import SALPY_ATCamera
import SALPY_ATSpectrograph
import SALPY_Script

index_gen = salobj.index_generator()

import sys
import logging
logger = logging.getLogger()
logger.level = logging.DEBUG


class Harness:
    def __init__(self):
        self.index = next(index_gen)
        self.test_index = next(index_gen)
        salobj.test_utils.set_random_lsst_dds_domain()
        self.script = ATCamTakeImage(index=self.index)
        self.atcam = salobj.Controller(SALPY_ATCamera)
        self.atspec = salobj.Controller(SALPY_ATSpectrograph)

        self.nimages = 0
        self.selected_filter = []
        self.selected_disperser = []
        self.selected_linear_stage = []

        self.atcam.cmd_takeImages.callback = self.cmd_take_images_callback
        self.atspec.cmd_changeFilter.callback = self.cmd_changeFilter_callback
        self.atspec.cmd_changeDisperser.callback = self.cmd_changeDisperser_callback
        self.atspec.cmd_moveLinearStage.callback = self.cmd_moveLinearStage_callback

    async def cmd_take_images_callback(self, id_data):
        one_exp_time = id_data.data.expTime \
                       + self.script.latiss.read_out_time + self.script.latiss.shutter_time
        await asyncio.sleep(one_exp_time*id_data.data.numImages)
        self.nimages += 1
        self.atcam.evt_endReadout.put()

    async def cmd_changeFilter_callback(self, id_data):
        self.selected_filter.append(id_data.data.filter)
        await asyncio.sleep(0.5)

    async def cmd_changeDisperser_callback(self, id_data):
        self.selected_disperser.append(id_data.data.disperser)
        await asyncio.sleep(0.5)

    async def cmd_moveLinearStage_callback(self, id_data):
        self.selected_linear_stage.append(id_data.data.distanceFromHome)
        await asyncio.sleep(0.5)


class TestATCamTakeImage(unittest.TestCase):

    def test_script_exp_time_scalar(self):
        async def doit():
            harness = Harness()
            exp_time = 5

            config_kwargs = dict(exp_times=exp_time)
            config_data = SALPY_Script.Script_command_configureC()
            config_data.config = yaml.safe_dump(config_kwargs)
            await harness.script.do_configure(id_data=salobj.CommandIdData(cmd_id=1,
                                                                           data=config_data))
            await harness.script.do_run(id_data=salobj.CommandIdData(cmd_id=2, data=None))

        asyncio.get_event_loop().run_until_complete(doit())

    def test_script_exp_time_array(self):
        async def doit():
            harness = Harness()
            exp_time_arr = (0, 5, 3)
            config_kwargs = dict(exp_times=exp_time_arr)
            config_data = SALPY_Script.Script_command_configureC()
            config_data.config = yaml.safe_dump(config_kwargs)
            await harness.script.do_configure(id_data=salobj.CommandIdData(cmd_id=1,
                                                                           data=config_data))
            await harness.script.do_run(id_data=salobj.CommandIdData(cmd_id=2, data=None))

        asyncio.get_event_loop().run_until_complete(doit())

    def test_take_images(self):
        async def doit():
            harness = Harness()

            config_kwargs = dict(nimages=1,
                                 exp_times=0.,
                                 filter=1,
                                 grating=1,
                                 linear_stage=100)
            config_data = SALPY_Script.Script_command_configureC()
            config_data.config = yaml.safe_dump(config_kwargs)

            await harness.script.do_configure(id_data=salobj.CommandIdData(cmd_id=1,
                                                                           data=config_data))
            await harness.script.do_run(id_data=salobj.CommandIdData(cmd_id=2, data=None))

            self.assertEqual(harness.nimages, config_kwargs['nimages'])
            self.assertEqual(len(harness.selected_filter), config_kwargs['nimages'])
            self.assertEqual(len(harness.selected_disperser), config_kwargs['nimages'])
            self.assertEqual(len(harness.selected_linear_stage), config_kwargs['nimages'])

            self.assertIn(config_kwargs['filter'], harness.selected_filter)
            self.assertIn(config_kwargs['grating'], harness.selected_disperser)
            self.assertIn(config_kwargs['linear_stage'], harness.selected_linear_stage)

        stream_handler = logging.StreamHandler(sys.stdout)
        logger.addHandler(stream_handler)

        asyncio.get_event_loop().run_until_complete(doit())


if __name__ == '__main__':
    unittest.main()
