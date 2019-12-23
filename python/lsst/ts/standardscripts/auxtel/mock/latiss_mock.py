
__all__ = ["LATISSMock"]

import asyncio
from lsst.ts import salobj


class LATISSMock:
    """Mock the behavior of the combined components that make out LATISS.

    This is useful for unit testing.
    """
    def __init__(self):

        self.atcam = salobj.Controller(name="ATCamera")
        self.atspec = salobj.Controller(name="ATSpectrograph")

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

        self.end_readout_task = None

        self.start_task = asyncio.gather(self.atspec.start_task,
                                         self.atcam.start_task)

    async def cmd_take_images_callback(self, data):
        """Emulate take image command."""
        one_exp_time = data.expTime + self.readout_time
        if data.shutter:
            one_exp_time += self.shutter_time
        await asyncio.sleep(one_exp_time*data.numImages)
        self.end_readout_task = asyncio.create_task(self.end_readout(data))

    async def end_readout(self, data):
        """Wait `self.readout_time` and send endReadout event."""
        await asyncio.sleep(self.readout_time)
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

    async def close(self):
        if self.end_readout_task is not None:
            try:
                await asyncio.wait_for(self.end_readout_task,
                                       timeout=self.readout_time*2.)
            except Exception:
                pass

        await asyncio.gather(self.atcam.close(),
                             self.atspec.close())

    async def __aenter__(self):
        await asyncio.gather(self.start_task)
        return self

    async def __aexit__(self, *args):
        await asyncio.gather(self.close())
