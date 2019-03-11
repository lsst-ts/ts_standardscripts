import sys
import unittest
import asyncio
import numpy as np
import logging

from lsst.ts import salobj

from lsst.ts.scriptqueue import ScriptState
from lsst.ts.standardscripts.auxtel.detector_characterization import ATGetStdFlatDataset

import SALPY_ATCamera
import SALPY_ATSpectrograph

np.random.seed(47)

index_gen = salobj.index_generator()

logger = logging.getLogger()
logger.level = logging.DEBUG


class Harness:
    def __init__(self):
        self.index = next(index_gen)

        self.test_index = next(index_gen)

        salobj.test_utils.set_random_lsst_dds_domain()

        self.script = ATGetStdFlatDataset(index=self.index)

        # Adds controller to Test
        self.at_cam = salobj.Controller(SALPY_ATCamera)
        self.at_spec = salobj.Controller(SALPY_ATSpectrograph)

        self.n_bias = 0
        self.n_dark = 0
        self.n_flat = 0

        self.filter = None
        self.grating = None
        self.linear_stage = None

    async def cmd_take_images_callback(self, id_data):
        if "bias" in id_data.data.imageSequenceName:
            self.n_bias += 1
        elif "dark" in id_data.data.imageSequenceName:
            self.n_dark += 1
        elif "flat" in id_data.data.imageSequenceName:
            self.n_flat += 1
        await asyncio.sleep(self.script.read_out_time)

        self.at_cam.evt_endReadout.put(self.at_cam.evt_endReadout.DataType())

    async def cmd_change_filter_callback(self, id_data):
        self.filter = id_data.data.filter

    async def cmd_change_grating_callback(self, id_data):
        self.grating = id_data.data.disperser

    async def cmd_move_linear_stage_callback(self, id_data):
        self.linear_stage = id_data.data.distanceFromHome


class TestATGetStdFlatDataset(unittest.TestCase):

    def test_script(self):
        async def doit():
            harness = Harness()

            harness.at_cam.cmd_takeImages.callback = harness.cmd_take_images_callback
            harness.at_spec.cmd_changeFilter.callback = harness.cmd_change_filter_callback
            harness.at_spec.cmd_changeDisperser.callback = harness.cmd_change_grating_callback
            harness.at_spec.cmd_moveLinearStage.callback = harness.cmd_move_linear_stage_callback

            # Make sure configuration works with no parameter
            await harness.script.configure()

            # Now configure the spectrograph
            await harness.script.configure(filter_id=0,
                                           grating_id=3,
                                           linear_stage=10.)

            harness.script.set_state(ScriptState.RUNNING)

            harness.script._run_task = asyncio.ensure_future(harness.script.run())
            await harness.script._run_task
            harness.script.set_state(ScriptState.ENDING)

            self.assertEqual(harness.n_bias, harness.script.n_bias * 2)
            self.assertEqual(harness.n_dark, harness.script.n_dark)
            self.assertEqual(harness.n_flat, len(harness.script.flat_dn_range) * harness.script.n_flat)
            self.assertEqual(harness.filter, 0)
            self.assertEqual(harness.grating, 3)
            self.assertEqual(harness.linear_stage, 10.)

        stream_handler = logging.StreamHandler(sys.stdout)
        logger.addHandler(stream_handler)

        asyncio.get_event_loop().run_until_complete(doit())


if __name__ == '__main__':
    unittest.main()
