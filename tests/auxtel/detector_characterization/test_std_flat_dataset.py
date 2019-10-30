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
import numpy as np
import logging

import yaml

from lsst.ts import salobj
from lsst.ts.idl.enums import Script
from lsst.ts.standardscripts.auxtel.detector_characterization import ATGetStdFlatDataset

np.random.seed(47)

index_gen = salobj.index_generator()

logging.basicConfig()


class Harness:
    def __init__(self):
        self.index = next(index_gen)
        salobj.test_utils.set_random_lsst_dds_domain()

        self.script = ATGetStdFlatDataset(index=self.index)

        # Adds controller to Test
        self.at_cam = salobj.Controller(name="ATCamera")
        self.at_spec = salobj.Controller(name="ATSpectrograph")

        self.n_bias = 0
        self.n_dark = 0
        self.n_flat = 0

        self.filter = None
        self.grating = None
        self.linear_stage = None

    async def cmd_take_images_callback(self, data):
        if "bias" in data.imageType.lower():
            self.n_bias += 1
        elif "dark" in data.imageType.lower():
            self.n_dark += 1
        elif "flat" in data.imageType.lower():
            self.n_flat += 1
        await asyncio.sleep(self.script.read_out_time)

        self.at_cam.evt_endReadout.put(self.at_cam.evt_endReadout.DataType())

    async def cmd_change_filter_callback(self, data):
        self.filter = data.filter

    async def cmd_change_grating_callback(self, data):
        self.grating = data.disperser

    async def cmd_move_linear_stage_callback(self, data):
        self.linear_stage = data.distanceFromHome

    async def __aenter__(self):
        await asyncio.gather(self.script.start_task,
                             self.at_cam.start_task,
                             self.at_spec.start_task)
        return self

    async def __aexit__(self, *args):
        await asyncio.gather(self.script.close(),
                             self.at_cam.close(),
                             self.at_spec.close())


class TestATGetStdFlatDataset(unittest.TestCase):

    def test_script(self):
        async def doit():
            async with Harness() as harness:
                harness.at_cam.cmd_takeImages.callback = harness.cmd_take_images_callback
                harness.at_spec.cmd_changeFilter.callback = harness.cmd_change_filter_callback
                harness.at_spec.cmd_changeDisperser.callback = harness.cmd_change_grating_callback
                harness.at_spec.cmd_moveLinearStage.callback = harness.cmd_move_linear_stage_callback

                # Make sure configure works with no data
                config_data = harness.script.cmd_configure.DataType()
                await harness.script.do_configure(config_data)
                harness.script.set_state(Script.ScriptState.UNCONFIGURED)

                # Now configure the spectrograph
                config_data.config = yaml.safe_dump(dict(filter=1,
                                                         grating=3,
                                                         linear_stage=10))
                await harness.script.do_configure(config_data)

                harness.script.set_state(Script.ScriptState.RUNNING)

                harness.script._run_task = asyncio.ensure_future(harness.script.run())
                await harness.script._run_task
                harness.script.set_state(Script.ScriptState.ENDING)

                self.assertEqual(harness.n_bias, harness.script.config.n_bias * 2)
                self.assertEqual(harness.n_dark, harness.script.config.n_dark)
                self.assertEqual(harness.n_flat,
                                 len(harness.script.config.flat_dn_range) * harness.script.config.n_flat)
                self.assertEqual(harness.filter, 1)
                self.assertEqual(harness.grating, 3)
                self.assertEqual(harness.linear_stage, 10)

        asyncio.get_event_loop().run_until_complete(doit())


if __name__ == '__main__':
    unittest.main()
