
__all__ = ["ATTCSMock"]

import asyncio
import numpy as np

from lsst.ts import salobj
from lsst.ts.idl.enums import ATDome

LONG_TIMEOUT = 30


class ATTCSMock:
    """ Mock the behavior of the combined components that make out ATTCS.

    This is useful for unit testing.

    """
    def __init__(self):

        self._components = ["ATMCS", "ATPtg", "ATAOS", "ATPneumatics",
                            "ATHexapod", "ATDome", "ATDomeTrajectory"]

        self.components = [comp.lower() for comp in self._components]

        # creating controllers for all components involved
        self.atmcs = salobj.Controller("ATMCS")
        self.atptg = salobj.Controller("ATPtg")
        self.atdome = salobj.Controller("ATDome")
        self.ataos = salobj.Controller("ATAOS")
        self.atpneumatics = salobj.Controller("ATPneumatics")
        self.athexapod = salobj.Controller("ATHexapod")
        self.atdometrajectory = salobj.Controller("ATDomeTrajectory")

        self.setting_versions = {}

        self.settings_to_apply = {}

        for comp in self.components:
            getattr(self, comp).cmd_start.callback = self.get_start_callback(comp)
            getattr(self, comp).cmd_enable.callback = self.get_enable_callback(comp)
            getattr(self, comp).cmd_disable.callback = self.get_disable_callback(comp)
            getattr(self, comp).cmd_standby.callback = self.get_standby_callback(comp)

        self.atdome.cmd_moveShutterMainDoor.callback = self.move_shutter_callback
        self.atdome.cmd_closeShutter.callback = self.close_shutter_callback
        self.atpneumatics.cmd_openM1Cover.callback = self.generic_callback
        self.atpneumatics.cmd_closeM1Cover.callback = self.generic_callback
        self.ataos.cmd_enableCorrection.callback = self.generic_callback
        self.ataos.cmd_disableCorrection.callback = self.generic_callback

        self.dome_shutter_pos = 0.

        self.slew_time = 10.

        self.tel_alt = 80.
        self.tel_az = 0.
        self.dom_az = 0.

        self.track = False

        self.start_task_finished = False
        self.start_task = asyncio.create_task(self.start_task_publish())

        self.task_list = []

        self.tel_pos_task = None
        self.dome_pos_task = None
        self.run_telemetry_loop = True

        self.atptg.cmd_raDecTarget.callback = self.fake_slew_callback
        self.atptg.cmd_azElTarget.callback = self.fake_slew_callback
        self.atptg.cmd_planetTarget.callback = self.fake_slew_callback
        self.atptg.cmd_stopTracking.callback = self.fake_stop_tracking

        self.atdome.cmd_moveAzimuth.callback = self.fake_move_dome

    async def start_task_publish(self):

        if self.start_task_finished:
            return

        await asyncio.gather(self.atmcs.start_task,
                             self.atptg.start_task,
                             self.atdome.start_task,
                             self.ataos.start_task,
                             self.atpneumatics.start_task,
                             self.athexapod.start_task,
                             self.atdometrajectory.start_task)

        for comp in self.components:
            getattr(self, comp).evt_summaryState.set_put(summaryState=salobj.State.STANDBY)
            self.setting_versions[comp] = f"test_{comp}"
            getattr(self, comp).evt_settingVersions.set_put(
                recommendedSettingsVersion=f"{self.setting_versions[comp]},"
            )

        self.atdome.evt_scbLink.set_put(active=True, force_output=True)
        self.run_telemetry_loop = True
        self.tel_pos_task = asyncio.create_task(self.fake_tel_pos_telemetry())
        self.dome_pos_task = asyncio.create_task(self.dome_tel_pos_telemetry())

        self.start_task_finished = True

    async def fake_tel_pos_telemetry(self):
        while self.run_telemetry_loop:

            self.atmcs.tel_mount_AzEl_Encoders.set_put(
                elevationCalculatedAngle=np.zeros(100)+self.tel_alt,
                azimuthCalculatedAngle=np.zeros(100)+self.tel_az,
            )

            if self.track:
                self.atmcs.evt_target.set_put(elevation=self.tel_alt,
                                              azimuth=self.tel_az,
                                              force_output=True)

            await asyncio.sleep(1.)

    async def dome_tel_pos_telemetry(self):
        while self.run_telemetry_loop:
            self.atdome.tel_position.set_put(azimuthPosition=self.dom_az)
            await asyncio.sleep(1.)

    async def atmcs_wait_and_fault(self, wait_time):
        self.atmcs.evt_summaryState.set_put(summaryState=salobj.State.ENABLED,
                                            force_output=True)
        await asyncio.sleep(wait_time)
        self.atmcs.evt_summaryState.set_put(summaryState=salobj.State.FAULT,
                                            force_output=True)

    async def atptg_wait_and_fault(self, wait_time):
        self.atptg.evt_summaryState.set_put(summaryState=salobj.State.ENABLED,
                                            force_output=True)
        await asyncio.sleep(wait_time)
        self.atptg.evt_summaryState.set_put(summaryState=salobj.State.FAULT,
                                            force_output=True)

    async def fake_slew_callback(self, id_data):
        """Fake slew waits 5 seconds, then reports all axes
           in position. Does not simulate the actual slew.
        """
        self.atmcs.evt_allAxesInPosition.set_put(inPosition=False,
                                                 force_output=True)
        self.atdome.evt_azimuthInPosition.set_put(inPosition=False,
                                                  force_output=True)
        self.track = True
        self.task_list.append(asyncio.create_task(self.wait_and_send_inposition()))

    async def fake_move_dome(self, data):
        self.atdome.evt_azimuthInPosition.set_put(inPosition=False,
                                                  force_output=True)

        await asyncio.sleep(self.slew_time)

        self.atdome.tel_position.set(azimuthPosition=data.azimuth)
        self.atdome.evt_azimuthInPosition.set_put(inPosition=True,
                                                  force_output=True)

    async def fake_stop_tracking(self, data):
        pass

    async def wait_and_send_inposition(self):

        await asyncio.sleep(self.slew_time)
        self.atmcs.evt_allAxesInPosition.set_put(inPosition=True,
                                                 force_output=True)
        await asyncio.sleep(0.5)
        self.atdome.evt_azimuthInPosition.set_put(inPosition=True,
                                                  force_output=True)

    async def generic_callback(self, id_data):
        await asyncio.sleep(0.5)

    async def move_shutter_callback(self, id_data):
        # This command returns right away in the current version of the dome.
        if id_data.open and self.dome_shutter_pos == 0.:
            self.task_list.append(asyncio.create_task(self.fake_open_shutter()))
        elif not id_data.open and self.dome_shutter_pos == 1.:
            self.task_list.append(asyncio.create_task(self.fake_close_shutter()))
        else:
            raise RuntimeError(f"Cannot execute operation: {id_data.open} with dome "
                               f"at {self.dome_shutter_pos}")

    async def close_shutter_callback(self, id_data):
        if self.dome_shutter_pos == 1.:
            self.task_list.append(asyncio.create_task(self.fake_close_shutter()))
        else:
            raise RuntimeError(f"Cannot close dome with dome "
                               f"at {self.dome_shutter_pos}")

    async def fake_open_shutter(self):
        self.atdome.evt_shutterInPosition.set_put(inPosition=False,
                                                  force_output=True)
        self.atdome.evt_mainDoorState.set_put(state=ATDome.ShutterDoorState.OPENING)
        for self.dome_shutter_pos in np.linspace(0., 1., 10):
            self.atdome.tel_position.set_put(mainDoorOpeningPercentage=self.dome_shutter_pos)
            await asyncio.sleep(self.slew_time/10.)
        self.atdome.evt_shutterInPosition.set_put(inPosition=True,
                                                  force_output=True)
        self.atdome.evt_mainDoorState.set_put(state=ATDome.ShutterDoorState.OPENED)

    async def fake_close_shutter(self):
        self.atdome.evt_shutterInPosition.set_put(inPosition=False,
                                                  force_output=True)
        self.atdome.evt_mainDoorState.set_put(state=ATDome.ShutterDoorState.CLOSING)
        for self.dome_shutter_pos in np.linspace(1., 0., 10):
            self.atdome.tel_position.set_put(mainDoorOpeningPercentage=self.dome_shutter_pos)
            await asyncio.sleep(self.slew_time/10.)
        self.atdome.evt_shutterInPosition.set_put(inPosition=True,
                                                  force_output=True)
        self.atdome.evt_mainDoorState.set_put(state=ATDome.ShutterDoorState.CLOSED)

    def get_start_callback(self, comp):

        def callback(id_data):

            ss = getattr(self, comp).evt_summaryState.data.summaryState

            if ss != salobj.State.STANDBY:
                raise RuntimeError(f"Current state is {salobj.State(ss.summaryState)}.")

            getattr(self, comp).evt_summaryState.set_put(summaryState=salobj.State.DISABLED)

            self.settings_to_apply[comp] = id_data.settingsToApply

        return callback

    def get_enable_callback(self, comp):

        def callback(id_data):
            ss = getattr(self, comp).evt_summaryState.data.summaryState

            if ss != salobj.State.DISABLED:
                raise RuntimeError(f"Current state is {salobj.State(ss.summaryState)}.")

            getattr(self, comp).evt_summaryState.set_put(summaryState=salobj.State.ENABLED)

        return callback

    def get_disable_callback(self, comp):

        def callback(id_data):
            ss = getattr(self, comp).evt_summaryState.data.summaryState

            if ss != salobj.State.ENABLED:
                raise RuntimeError(f"Current state is {salobj.State(ss.summaryState)}.")

            getattr(self, comp).evt_summaryState.set_put(summaryState=salobj.State.DISABLED)

        return callback

    def get_standby_callback(self, comp):

        def callback(id_data):
            ss = getattr(self, comp).evt_summaryState.data.summaryState

            if ss != salobj.State.DISABLED:
                raise RuntimeError(f"Current state is {salobj.State(ss.summaryState)}.")

            getattr(self, comp).evt_summaryState.set_put(summaryState=salobj.State.STANDBY)

        return callback

    async def close(self):

        # await all tasks created during runtime

        try:
            await asyncio.wait_for(asyncio.gather(*self.task_list),
                                   timeout=LONG_TIMEOUT)

            self.run_telemetry_loop = False

            await asyncio.gather(self.tel_pos_task,
                                 self.dome_pos_task)

        except Exception:
            pass

        close_task = []

        for comp in self.components:
            close_task.append(getattr(self, comp).close())

        await asyncio.gather(*close_task)

    async def __aenter__(self):

        await self.start_task

        return self

    async def __aexit__(self, *args):

        await self.close()
