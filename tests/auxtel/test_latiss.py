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

import unittest
import asyncio

from lsst.ts import salobj
from lsst.ts.standardscripts.auxtel.latiss import LATISS

index_gen = salobj.index_generator()


class Harness:
    def __init__(self):
        self.index = next(index_gen)
        self.test_index = next(index_gen)
        salobj.test_utils.set_random_lsst_dds_domain()

        self.atcam = salobj.Controller(name="ATCamera")
        self.atspec = salobj.Controller(name="ATSpectrograph")

        self.domain = salobj.Domain()
        self.latiss = LATISS(salobj.Remote(domain=self.atcam.domain, name="ATCamera"),
                             salobj.Remote(domain=self.atspec.domain, name="ATSpectrograph"))

        self.atcam.cmd_takeImages.callback = self.cmd_take_images_callback
        self.atspec.cmd_changeFilter.callback = self.cmd_changeFilter_callback
        self.atspec.cmd_changeDisperser.callback = self.cmd_changeDisperser_callback
        self.atspec.cmd_moveLinearStage.callback = self.cmd_moveLinearStage_callback

        self.readout_time = 2.
        self.shutter_time = 1.

        self.nimages = 0
        self.exptime_list = []

        self.latiss_filter = None
        self.latiss_grating = None
        self.latiss_linear_stage = None

    async def cmd_take_images_callback(self, data):
        """Emulate take image command."""
        one_exp_time = data.expTime + self.readout_time
        if data.shutter:
            one_exp_time += self.shutter_time
        await asyncio.sleep(one_exp_time*data.numImages)
        self.atcam.evt_endReadout.put()
        self.nimages += 1
        self.exptime_list.append(data.expTime)

    async def cmd_changeFilter_callback(self, data):
        """Emulate change filter command"""
        await asyncio.sleep(0.1)
        self.atspec.evt_filterInPosition.put()
        self.atspec.evt_reportedFilterPosition.put()
        self.latiss_filter = data.filter

    async def cmd_changeDisperser_callback(self, data):
        """Emulate change filter command"""
        await asyncio.sleep(0.1)
        self.atspec.evt_disperserInPosition.put()
        self.atspec.evt_reportedDisperserPosition.put()
        self.latiss_grating = data.disperser

    async def cmd_moveLinearStage_callback(self, data):
        """Emulate change filter command"""
        await asyncio.sleep(0.1)
        self.atspec.evt_linearStageInPosition.put()
        self.atspec.evt_reportedLinearStagePosition.put()
        self.latiss_linear_stage = data.distanceFromHome

    async def __aenter__(self):
        await asyncio.gather(self.latiss.atcam.start_task,
                             self.latiss.atspec.start_task,
                             self.atcam.start_task,
                             self.atspec.start_task)
        return self

    async def __aexit__(self, *args):
        await asyncio.gather(self.atcam.close(),
                             self.atspec.close())


class TestLATISS(unittest.TestCase):

    def test_take_bias(self):
        async def doit():
            async with Harness() as harness:
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
            async with Harness() as harness:
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
            async with Harness() as harness:
                nflats = 10
                exptime = 5.
                filter_id = 1
                grating_id = 1
                linear_stage = 100.

                await harness.latiss.take_flats(nflats=nflats,
                                                exptime=exptime,
                                                filter=filter_id,
                                                grating=grating_id,
                                                linear_stage=linear_stage)
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
