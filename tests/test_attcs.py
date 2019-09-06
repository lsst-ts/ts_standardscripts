from lsst.ts.standardscripts.auxtel.attcs import ATTCS
import unittest
import asyncio
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

        self.domain = salobj.Domain()

        self.attcs = ATTCS(salobj.Remote(self.domain, "ATMCS"),
                           salobj.Remote(self.domain, "ATPtg"),
                           salobj.Remote(self.domain, "ATAOS"),
                           salobj.Remote(self.domain, "ATPneumatics"),
                           salobj.Remote(self.domain, "ATHexapod"),
                           salobj.Remote(self.domain, "ATDome"),
                           salobj.Remote(self.domain, "ATDomeTrajectory"),
                           check={"atpneumatics": False,
                                  "athexapod": False,
                                  "atdome": True,
                                  "atdometrajectory": True})

        self.slew_time = 10.

        self.atptg.cmd_raDecTarget.callback = self.fake_slew_callback
        self.atptg.cmd_planetTarget.callback = self.fake_slew_callback

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
        asyncio.ensure_future(self.wait_and_send_inposition())

    async def wait_and_send_inposition(self):

        await asyncio.sleep(self.slew_time)
        self.atmcs.evt_allAxesInPosition.set_put(inPosition=True,
                                                 force_output=True)

    async def __aenter__(self):
        await asyncio.gather(self.attcs.atmcs.start_task,
                             self.attcs.atptg.start_task,
                             self.attcs.ataos.start_task,
                             self.attcs.atpneumatics.start_task,
                             self.attcs.athexapod.start_task,
                             self.attcs.atdome.start_task,
                             self.attcs.atdometrajectory.start_task)
        return self

    async def __aexit__(self, *args):
        await asyncio.gather(self.domain.close(),
                             self.atmcs.close(),
                             self.atptg.close())


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


if __name__ == '__main__':
    unittest.main()
