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

        self.script = ATGetStdFlatDataset(index=self.index, descr='Test ATGetStdFlatDataset')

        # Adds controller to Test
        self.at_cam = salobj.Controller(SALPY_ATCamera)
        self.at_spec = salobj.Controller(SALPY_ATSpectrograph)

        self.nbias = 0
        self.ndark = 0
        self.nflat = 0

    async def cmd_take_images_callback(self, id_data):
        if "bias" in id_data.data.imageSequenceName:
            self.nbias += 1
        elif "dark" in id_data.data.imageSequenceName:
            self.ndark += 1
        elif "flat" in id_data.data.imageSequenceName:
            self.nflat += 1
        await asyncio.sleep(self.script.read_out_time)

        self.at_cam.evt_endReadout.put(self.at_cam.evt_endReadout.DataType())


class TestATGetStdFlatDataset(unittest.TestCase):

    def test_script(self):
        async def doit():
            harness = Harness()

            # Adds callback to take image command
            harness.at_cam.cmd_takeImages.callback = harness.cmd_take_images_callback

            await harness.script.configure()

            harness.script.set_state(ScriptState.RUNNING)

            harness.script._run_task = asyncio.ensure_future(harness.script.run())
            await harness.script._run_task
            harness.script.set_state(ScriptState.ENDING)

            self.assertEqual(harness.nbias, harness.script.n_bias*2)
            self.assertEqual(harness.ndark, harness.script.n_dark)
            self.assertEqual(harness.nflat, len(harness.script.flat_dn_range)*harness.script.n_flat)

        stream_handler = logging.StreamHandler(sys.stdout)
        logger.addHandler(stream_handler)

        asyncio.get_event_loop().run_until_complete(doit())


if __name__ == '__main__':
    unittest.main()
