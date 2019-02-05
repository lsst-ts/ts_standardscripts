__all__ = ["BobHoskins"]
"""The script module
"""

import SALPY_LinearStage
import SALPY_Electrometer
import SALPY_TunableLaser
from lsst.ts.scriptqueue import BaseScript
from lsst.ts.salobj import Remote
import asyncio


class BobHoskins(BaseScript):
    """docstring for BobHoskins

    A SAL script that is used for testing two lab LinearStages, the TunableLaser and an Electrometer.
    It propagates the laser at a wavelength while the two linear stages move in a grid pattern in a given
    step increment. At each step, an electrometer will take a reading. The data will then be pushed into 
    a csv file and then plotted as coordinate vs. electrometer reading.

    Parameters
    ----------
    index: int
        The SAL index of the script.
    descr: str
        A short description of script's purpose.

    Attributes
    ----------
    wanted_remotes: list
    wavelengths: range
    steps: int
    linear_stage_set: bool
    linear_stage_2_set: bool
    electrometer_set: bool
    tunable_laser_set: bool
    """
    def __init__(self, index, descr):
        super().__init__(index, descr, remotes_dict={
            'linear_stage_1': Remote(SALPY_LinearStage, 1),
            'linear_stage_2': Remote(SALPY_LinearStage, 2),
            'electrometer': Remote(SALPY_Electrometer, 1),
            'tunable_laser': Remote(SALPY_TunableLaser)
        })
        self.wanted_remotes = None
        self.wavelengths = None
        self.steps = None
        self.linear_stage_set = False
        self.linear_stage_2_set = False
        self.electrometer_set = False
        self.tunable_laser_set = False

    def set_metadata(self,metadata):
        metadata = {'remotes_set': [self.linear_stage_set,self.linear_stage_2_set,self.electrometer_set,self.tunable_laser_set], 'time': 'NaN'}
        return metadata

    def setup_devices(self):
        if tunable_laser_set:
            self.propagate = True
            self.get_summary_state()
            if self.summary_state_tl is not None:
                pass

            
    def get_summary_state(self):
        self.summary_state_ls1 = self.linear_stage_1.evt_summaryState.get()
        self.summary_state_ls2 = self.linear_stage_2.evt_summaryState.get()
        self.summary_state_tl = self.tunable_laser.evt_summaryState.get()
        self.summary_state_e = self.electrometer.evt_summaryState.get()

    def move_ls_1(self):
        pass

    def move_ls_2(self):
        pass

    def read_electrometer(self):
        pass

    def run(self):
        if self.tunable_laser_set:
            self.propagate = True
            start_propagate_cmd = self.tunable_laser.cmd_startPropagation.DataType()
            await start_propagate_ack = self.tunable_laser.cmd_startPropagation.start(start_propagate_cmd,timeout=10)
            if start_progagate_ack.ack.ack is not 303:
                raise ValueError("Script knows not what to do in this situation")
        else:
            self.propagate = False
            self.wavelengths = 525
        for wavelength in self.wavelengths:
            if self.linear_stage_set:
                enable_cmd = self.linear_stage_1.cmd_enable.DataType()
                await enable_ack = self.linear_stage_1.cmd_enable.start(enable_cmd,timeout=10)
                if enable_ack.ack.ack is not 303:
                    raise ValueError("Script knows not what to do in this situation")
            for ls_pos in range(1,75,self.steps):
                move_ls1_topic = self.linear_stage_1.cmd_moveAbsolute.DataType()
                move_ls1_topic.distance = ls_pos
                move_ls1_ack = self.linear_stage_1.cmd_moveAbsolute.start(move_ls1_topic,timeout=10)
                if move_ls1_ack.ack.ack is not 303:
                    raise ValueError("Script knows not what to do in this situation")
                for ls_2_pos in range(1,75,self.steps):
                    move_ls2_topic = self.linear_stage_2.cmd_moveAbsolute.DataType()
                    move_ls2_topic.distance = ls_2_pos
                    await move_ls2_ack = self.linear_stage_2.cmd_moveAbsolute.start(move_ls2_topic,timeout=10)
                    if move_ls2_ack.ack.ack is not 303:
                        raise ValueError("Script does not know what to do in this situation")
                    electrometer_scan_topic = self.electrometer.cmd_startScanDt.DataType()
                    electrometer_scan_topic.scanDuration = 1
                    await electrometer_scan_ack = self.electrometer.cmd_startScanDt.start(electrometer_scan_topic,timeout=10)
                    if electrometer_scan_ack.ack.ack is not 303:
                        raise ValueError("Script does not know what to do in this situation")

    def configure(self, wanted_remotes, wavelengths, steps=5):
        """Configures the script.

        Parameters
        ----------
        wanted_remotes: list
            A list of remotes_names that should be used for running the script.
            full list:['linear_stage_1_remote','linear_stage_2_remote','electrometer_remote',
            'tunable_laser_remote']
        wavelengths: range
            A range of wavelengths to iterate through.
        steps: int (the default is 5 mm)
            The amount of mm to move the linear stages by.
        """
        self.wanted_remotes = wanted_remotes
        self.wavelengths = range(wavelengths[0], wavelengths[1])
        self.steps = steps
        if 'linear_stage_1_remote' in self.wanted_remotes:
            self.linear_stage_set = True
        if 'linear_stage_2_remote' in self.wanted_remotes:
            self.linear_stage_2_set = True
        if 'electrometer_remote' in self.wanted_remotes:
            self.electrometer_set = True
        if 'tunable_laser_remote' in self.wanted_remotes:
            self.tunable_laser_set = True
