import unittest
import asyncio
import numpy as np

from lsst.ts import salobj
from lsst.ts.standardscripts.auxtel.latiss import LATISS

import SALPY_ATCamera
import SALPY_ATSpectrograph

index_gen = salobj.index_generator()


class Harness:
    def __init__(self):
        self.index = next(index_gen)
        self.test_index = next(index_gen)
        salobj.test_utils.set_random_lsst_dds_domain()
        self.latiss = LATISS(salobj.Remote(SALPY_ATCamera),
                             salobj.Remote(SALPY_ATSpectrograph))
        self.atcam = salobj.Controller(SALPY_ATCamera)
        self.atspec = salobj.Controller(SALPY_ATSpectrograph)

        self.readout_time = 2.
        self.shutter_time = 1.

        self.nimages = 0
        self.exptime_list = []

        self.latiss_filter = None
        self.latiss_grating = None
        self.latiss_linear_stage = None

    async def cmd_take_images_callback(self, id_data):
        """Emulate take image command."""
        one_exp_time = id_data.data.expTime + self.readout_time
        if id_data.data.shutter:
            one_exp_time += self.shutter_time
        await asyncio.sleep(one_exp_time*id_data.data.numImages)
        self.atcam.evt_endReadout.put()
        self.nimages += 1
        self.exptime_list.append(id_data.data.expTime)

    async def cmd_changeFilter_callback(self, id_data):
        """Emulate change filter command"""
        await asyncio.sleep(0.1)
        self.atspec.evt_filterInPosition.put()
        self.atspec.evt_reportedFilterPosition.put()
        self.latiss_filter = id_data.data.filter

    async def cmd_changeDisperser_callback(self, id_data):
        """Emulate change filter command"""
        await asyncio.sleep(0.1)
        self.atspec.evt_disperserInPosition.put()
        self.atspec.evt_reportedDisperserPosition.put()
        self.latiss_grating = id_data.data.disperser

    async def cmd_moveLinearStage_callback(self, id_data):
        """Emulate change filter command"""
        await asyncio.sleep(0.1)
        self.atspec.evt_linearStageInPosition.put()
        self.atspec.evt_reportedLinearStagePosition.put()
        self.latiss_linear_stage = id_data.data.distanceFromHome


class TestLATISS(unittest.TestCase):

    def test_take_bias(self):
        async def doit():
            harness = Harness()
            harness.atcam.cmd_takeImages.callback = harness.cmd_take_images_callback
            nbias = 10
            await harness.latiss.take_bias(nbias=nbias)
            self.assertEqual(harness.nimages, nbias)
            self.assertEqual(len(harness.exptime_list), nbias)
            for i in range(nbias):
                self.assertEqual(harness.exptime_list[i], 0.)
            self.assertIsNone(harness.latiss_linear_stage)
            self.assertIsNone(harness.latiss_grating)
            self.assertIsNone(harness.latiss_filter)

        asyncio.get_event_loop().run_until_complete(doit())

    def test_take_darks(self):
        async def doit():
            harness = Harness()
            harness.atcam.cmd_takeImages.callback = harness.cmd_take_images_callback
            ndarks = 10
            exptime = 5.
            await harness.latiss.take_darks(ndarks=ndarks,
                                            exptime=exptime)
            self.assertEqual(harness.nimages, ndarks)
            self.assertEqual(len(harness.exptime_list), ndarks)
            for i in range(ndarks):
                self.assertEqual(harness.exptime_list[i], exptime)
            self.assertIsNone(harness.latiss_linear_stage)
            self.assertIsNone(harness.latiss_grating)
            self.assertIsNone(harness.latiss_filter)

        asyncio.get_event_loop().run_until_complete(doit())

    def test_take_flats(self):
        async def doit():
            harness = Harness()
            harness.atcam.cmd_takeImages.callback = harness.cmd_take_images_callback
            harness.atspec.cmd_changeFilter.callback = harness.cmd_changeFilter_callback
            harness.atspec.cmd_changeDisperser.callback = harness.cmd_changeDisperser_callback
            harness.atspec.cmd_moveLinearStage.callback = harness.cmd_moveLinearStage_callback

            nflats = 10
            exptime = 5.
            filter_id = 1
            grating_id = 1
            linear_stage = 100.

            await harness.latiss.take_flats(nflats=nflats,
                                            exptime=exptime,
                                            latiss_filter=filter_id,
                                            latiss_grating=grating_id,
                                            latiss_linear_stage=linear_stage)
            self.assertEqual(harness.nimages, nflats)
            self.assertEqual(len(harness.exptime_list), nflats)
            for i in range(nflats):
                self.assertEqual(harness.exptime_list[i], exptime)
            self.assertEqual(harness.latiss_filter, filter_id)
            self.assertEqual(harness.latiss_grating, grating_id)
            self.assertEqual(harness.latiss_linear_stage, linear_stage)

        asyncio.get_event_loop().run_until_complete(doit())


if __name__ == '__main__':
    unittest.main()
