from lsst.ts.standardscripts.auxtel.attcs import ATTCS
import unittest
import asyncio
import numpy as np

from lsst.ts import salobj
from lsst.ts.salobj import test_utils
from lsst.ts.idl.enums import ATPtg
import logging
# from math import isclose

logger = logging.getLogger()
logger.level = logging.DEBUG

index_gen = salobj.index_generator()


class Harness:
    def __init__(self):

        self.log = logging.getLogger("Harness")

        test_utils.set_random_lsst_dds_domain()

        self.atmcs = salobj.Controller("ATMCS")
        self.atptg = salobj.Controller("ATPtg")
        self.atdome = salobj.Controller("ATDome")
        self.ataos = salobj.Controller("ATAOS")
        self.atpneumatics = salobj.Controller("ATPneumatics")
        self.athexapod = salobj.Controller("ATHexapod")
        self.atdometrajectory = salobj.Controller("ATDomeTrajectory")

        self.setting_versions = {}

        self.settings_to_apply = {}

        self.attcs = ATTCS(indexed_dome=False)

        for comp in self.attcs.components:
            getattr(self, comp).evt_summaryState.set_put(summaryState=salobj.State.STANDBY)
            self.setting_versions[comp] = f"test_{comp}"
            getattr(self, comp).evt_settingVersions.set_put(
                recommendedSettingsVersion=f"{self.setting_versions[comp]},"
            )
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

        self.atdome.evt_scbLink.set_put(active=True, force_output=True)

        self.dome_shutter_pos = 0.

        self.slew_time = 10.

        self.tel_alt = 80.
        self.tel_az = 0.
        self.dom_az = 0.

        self.track = False

        self.tel_pos_task = asyncio.ensure_future(self.fake_tel_pos_telemetry())
        self.dome_pos_task = asyncio.ensure_future(self.dome_tel_pos_telemetry())
        self.run_telemetry_loop = True

        self.atptg.cmd_raDecTarget.callback = self.fake_slew_callback
        self.atptg.cmd_planetTarget.callback = self.fake_slew_callback

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
        self.log.debug("atmcs ENABLED")
        self.atmcs.evt_summaryState.set_put(summaryState=salobj.State.ENABLED,
                                            force_output=True)
        await asyncio.sleep(wait_time)
        self.log.debug("atmcs FAULT")
        self.atmcs.evt_summaryState.set_put(summaryState=salobj.State.FAULT,
                                            force_output=True)

    async def atptg_wait_and_fault(self, wait_time):
        self.log.debug("atptg ENABLED")
        self.atptg.evt_summaryState.set_put(summaryState=salobj.State.ENABLED,
                                            force_output=True)
        await asyncio.sleep(wait_time)
        self.log.debug("atptg FAULT")
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
        asyncio.ensure_future(self.wait_and_send_inposition())

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
            asyncio.ensure_future(self.fake_open_shutter())
        elif not id_data.open and self.dome_shutter_pos == 1.:
            asyncio.ensure_future(self.fake_close_shutter())
        else:
            raise RuntimeError(f"Cannot execute operation: {id_data.open} with dome "
                               f"at {self.dome_shutter_pos}")

    async def close_shutter_callback(self, id_data):
        if self.dome_shutter_pos == 1.:
            asyncio.ensure_future(self.fake_close_shutter())
        else:
            raise RuntimeError(f"Cannot close dome with dome "
                               f"at {self.dome_shutter_pos}")

    async def fake_open_shutter(self):
        self.atdome.evt_shutterInPosition.set_put(inPosition=False,
                                                  force_output=True)
        for self.dome_shutter_pos in np.linspace(0., 1., 10):
            self.atdome.tel_position.set_put(mainDoorOpeningPercentage=self.dome_shutter_pos)
            await asyncio.sleep(self.slew_time/10.)
        self.atdome.evt_shutterInPosition.set_put(inPosition=True,
                                                  force_output=True)

    async def fake_close_shutter(self):
        self.atdome.evt_shutterInPosition.set_put(inPosition=False,
                                                  force_output=True)
        for self.dome_shutter_pos in np.linspace(1., 0., 10):
            self.atdome.tel_position.set_put(mainDoorOpeningPercentage=self.dome_shutter_pos)
            await asyncio.sleep(self.slew_time/10.)
        self.atdome.evt_shutterInPosition.set_put(inPosition=True,
                                                  force_output=True)

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

    async def __aenter__(self):

        start_task = [self.attcs.start_task]

        for comp in self.attcs.components:
            start_task.append(getattr(self, comp).start_task)

        await asyncio.gather(*start_task)

        return self

    async def __aexit__(self, *args):
        self.run_telemetry_loop = False

        close_task = [self.tel_pos_task,
                      self.dome_pos_task,
                      self.attcs.close()]

        for comp in self.attcs.components:
            close_task.append(getattr(self, comp).close())

        await asyncio.gather(*close_task)


class TestATTCS(unittest.TestCase):

    def test_slew(self):

        async def runtest():

            async with Harness() as harness:

                ra = 0.
                dec = -30.

                harness.log.debug("test 1 start")

                with self.subTest(ra=ra, dec=dec):
                    await harness.attcs.slew(ra, dec, slew_timeout=harness.slew_time*2.)

                harness.log.debug("test 2 start")

                with self.subTest(msg="Ra/Dec: Fail ATPtg FAULT", component="ATPtg"):
                    with self.assertRaises(RuntimeError):
                        ret_val = await asyncio.gather(
                            harness.attcs.slew(ra, dec,
                                               slew_timeout=harness.slew_time*2.),
                            harness.atptg_wait_and_fault(1.),
                            return_exceptions=True)
                        for val in ret_val:
                            harness.log.debug(f"retval: {val!r}")

                        for val in ret_val:
                            if isinstance(val, Exception):
                                raise val

                harness.log.debug("test 3 start")

                with self.subTest(msg="Ra/Dec: Fail ATMCS FAULT", component="ATMCS"):
                    with self.assertRaises(RuntimeError):

                        ret_val = await asyncio.gather(
                            harness.attcs.slew(ra, dec, slew_timeout=harness.slew_time*2.),
                            harness.atmcs_wait_and_fault(1.),
                            return_exceptions=True)

                        for val in ret_val:
                            harness.log.debug(f"retval: {val!r}")

                        for val in ret_val:
                            if isinstance(val, Exception):
                                raise val

                harness.log.debug("test 4 start")

                for planet in ATPtg.Planets:
                    with self.subTest(planet=planet):
                        await harness.attcs.slew_to_planet(planet,
                                                           slew_timeout=harness.slew_time*2.)

                harness.log.debug("test 5 start")

                with self.subTest(msg="Planet: Fail ATMCS FAULT", component="ATMCS"):
                    with self.assertRaises(RuntimeError):
                        ret_val = await asyncio.gather(
                            harness.attcs.slew_to_planet(
                                ATPtg.Planets.JUPITER,
                                slew_timeout=harness.slew_time*2.),
                            harness.atmcs_wait_and_fault(1.),
                            return_exceptions=True)
                        for val in ret_val:
                            if isinstance(val, Exception):
                                raise val
                            else:
                                harness.log.debug(f"ret_val: {val}")

                harness.log.debug("test 6 start")

                with self.subTest(msg="Planet: Fail ATPtg FAULT", component="ATPtg"):
                    with self.assertRaises(RuntimeError):
                        ret_val = await asyncio.gather(
                            harness.attcs.slew_to_planet(
                                ATPtg.Planets.JUPITER,
                                slew_timeout=harness.slew_time*2.),
                            harness.atptg_wait_and_fault(1.),
                            return_exceptions=True)
                        for val in ret_val:
                            if isinstance(val, Exception):
                                raise val
                            else:
                                harness.log.debug(f"ret_val: {val}")

                harness.log.debug("test done")

        asyncio.get_event_loop().run_until_complete(runtest())

    def test_startup_shutdown(self):

        async def runtest():

            async with Harness() as harness:

                settings = dict(zip(harness.attcs.components,
                                    [f'setting4_{c}' for c in harness.attcs.components]))

                await harness.attcs.startup(settings)

                await harness.attcs.shutdown()

        asyncio.get_event_loop().run_until_complete(runtest())


if __name__ == '__main__':
    unittest.main()
