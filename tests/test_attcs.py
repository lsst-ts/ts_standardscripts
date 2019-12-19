
import unittest
import asynctest
import asyncio

from lsst.ts import salobj
from lsst.ts.salobj import test_utils
from lsst.ts.idl.enums import ATPtg
import logging

from lsst.ts.standardscripts.auxtel.attcs import ATTCS
from lsst.ts.standardscripts.auxtel.mock import ATTCSMock

logger = logging.getLogger()
logger.level = logging.DEBUG

index_gen = salobj.index_generator()


class Harness:
    def __init__(self):

        self.log = logging.getLogger("Harness")

        test_utils.set_random_lsst_dds_domain()

        self.attcs_mock = ATTCSMock()

        self.atmcs = self.attcs_mock.atmcs
        self.atptg = self.attcs_mock.atptg
        self.atdome = self.attcs_mock.atdome
        self.ataos = self.attcs_mock.ataos
        self.atpneumatics = self.attcs_mock.atpneumatics
        self.athexapod = self.attcs_mock.athexapod
        self.atdometrajectory = self.attcs_mock.atdometrajectory

        self.attcs = ATTCS(indexed_dome=False)

    async def __aenter__(self):

        await asyncio.gather(self.attcs.start_task, self.attcs_mock.start_task)

        return self

    async def __aexit__(self, *args):

        await asyncio.gather(self.attcs.close(),
                             self.attcs_mock.close())


class TestATTCS(asynctest.TestCase):

    async def test_slew(self):

        async with Harness() as harness:

            await harness.attcs.startup()

            ra = 0.
            dec = -30.

            harness.log.debug("test 1 start")

            with self.subTest(ra=ra, dec=dec):
                await harness.attcs.slew(ra, dec, slew_timeout=harness.attcs_mock.slew_time*2.)

            harness.log.debug("test 2 start")

            with self.subTest(msg="Ra/Dec: Fail ATPtg FAULT", component="ATPtg"):
                with self.assertRaises(RuntimeError):
                    ret_val = await asyncio.gather(
                        harness.attcs.slew(ra, dec,
                                           slew_timeout=harness.attcs_mock.slew_time*2.),
                        harness.attcs_mock.atptg_wait_and_fault(1.),
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
                        harness.attcs.slew(ra, dec, slew_timeout=harness.attcs_mock.slew_time*2.),
                        harness.attcs_mock.atmcs_wait_and_fault(1.),
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
                                                       slew_timeout=harness.attcs_mock.slew_time*2.)

            harness.log.debug("test 5 start")

            with self.subTest(msg="Planet: Fail ATMCS FAULT", component="ATMCS"):
                with self.assertRaises(RuntimeError):
                    ret_val = await asyncio.gather(
                        harness.attcs.slew_to_planet(
                            ATPtg.Planets.JUPITER,
                            slew_timeout=harness.attcs_mock.slew_time*2.),
                        harness.attcs_mock.atmcs_wait_and_fault(1.),
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
                            slew_timeout=harness.attcs_mock.slew_time*2.),
                        harness.attcs_mock.atptg_wait_and_fault(1.),
                        return_exceptions=True)
                    for val in ret_val:
                        if isinstance(val, Exception):
                            raise val
                        else:
                            harness.log.debug(f"ret_val: {val}")

            harness.log.debug("test done")

    async def test_startup_shutdown(self):

        async with Harness() as harness:

            # Testing when passing settings for all components

            settings = dict(zip(harness.attcs.components,
                                [f'setting4_{c}' for c in harness.attcs.components]))

            await harness.attcs.startup(settings)

            for comp in settings:
                self.assertEqual(harness.attcs_mock.settings_to_apply[comp],
                                 settings[comp])

            await harness.attcs.shutdown()

            # Testing when not passing settings for all components and only
            # atdome and ataos sent evt_settingVersions.
            # atdome sent a single label but ataos sends more then one.

            harness.atdome.evt_settingVersions.set_put(
                recommendedSettingsLabels="setting4_atdome_set")

            harness.ataos.evt_settingVersions.set_put(
                recommendedSettingsLabels="setting4_ataos_set1,setting4_ataos2_set2")

            # Give remotes some time to update their data.
            await asyncio.sleep(harness.attcs.fast_timeout)

            await harness.attcs.startup()

            for comp in harness.attcs.components:
                if comp == "atdome":
                    self.assertEqual(harness.attcs_mock.settings_to_apply[comp],
                                     "setting4_atdome_set")
                elif comp == "ataos":
                    self.assertEqual(harness.attcs_mock.settings_to_apply[comp],
                                     "setting4_ataos_set1")
                else:
                    self.assertEqual(harness.attcs_mock.settings_to_apply[comp],
                                     "")


if __name__ == '__main__':
    unittest.main()
