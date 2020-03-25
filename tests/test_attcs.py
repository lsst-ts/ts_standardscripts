import asyncio
import logging
import random
import unittest

import asynctest

from lsst.ts.idl.enums import ATPtg

from lsst.ts import standardscripts
from lsst.ts.standardscripts.auxtel.attcs import ATTCS
from lsst.ts.standardscripts.auxtel.mock import ATTCSMock

HB_TIMEOUT = 5  # Basic timeout for heartbeats
MAKE_TIMEOUT = 60  # Timeout for make_script (sec)

random.seed(47)  # for set_random_lsst_dds_domain

logging.basicConfig(level=logging.DEBUG)


class TestATTCS(standardscripts.BaseScriptTestCase, asynctest.TestCase):
    async def basic_make_script(self, index):
        self.attcs_mock = ATTCSMock()

        self.atmcs = self.attcs_mock.atmcs
        self.atptg = self.attcs_mock.atptg
        self.atdome = self.attcs_mock.atdome
        self.ataos = self.attcs_mock.ataos
        self.atpneumatics = self.attcs_mock.atpneumatics
        self.athexapod = self.attcs_mock.athexapod
        self.atdometrajectory = self.attcs_mock.atdometrajectory

        self.attcs = ATTCS()

        return (self.attcs, self.attcs_mock)

    async def test_slew(self):

        async with self.make_script(timeout=MAKE_TIMEOUT):

            print("wait for attcs.startup")
            await self.attcs.startup()

            ra = 0.0
            dec = -30.0

            print("test 1 start")

            await self.attcs.slew(ra, dec, slew_timeout=self.attcs_mock.slew_time * 2.0)

    async def test_slew_fail_atptg_fault(self):

        async with self.make_script(timeout=MAKE_TIMEOUT):
            print("wait for attcs.startup")
            await self.attcs.startup()

            ra = 0.0
            dec = -30.0

            print("test 2 start")

            with self.assertRaises(RuntimeError):
                ret_val = await asyncio.gather(
                    self.attcs.slew(
                        ra, dec, slew_timeout=self.attcs_mock.slew_time * 2.0
                    ),
                    self.attcs_mock.atptg_wait_and_fault(1.0),
                    return_exceptions=True,
                )
                for val in ret_val:
                    print(f"retval: {val!r}")

                for val in ret_val:
                    if isinstance(val, Exception):
                        raise val

    async def test_slew_fail_atmcs_fault(self):

        async with self.make_script(timeout=MAKE_TIMEOUT):
            print("wait for attcs.startup")
            await self.attcs.startup()

            ra = 0.0
            dec = -30.0

            print("test 3 start")

            with self.assertRaises(RuntimeError):

                ret_val = await asyncio.gather(
                    self.attcs.slew(
                        ra, dec, slew_timeout=self.attcs_mock.slew_time * 2.0
                    ),
                    self.attcs_mock.atmcs_wait_and_fault(1.0),
                    return_exceptions=True,
                )

                for val in ret_val:
                    print(f"retval: {val!r}")

                for val in ret_val:
                    if isinstance(val, Exception):
                        raise val

    async def test_slew_toplanet(self):

        async with self.make_script(timeout=MAKE_TIMEOUT):
            print("wait for attcs.startup")
            await self.attcs.startup()

            print("test 4 start")

            for planet in ATPtg.Planets:
                with self.subTest(planet=planet):
                    await self.attcs.slew_to_planet(
                        planet, slew_timeout=self.attcs_mock.slew_time * 2.0
                    )

    async def test_slew_toplanet_fail_atmcs_fault(self):

        async with self.make_script(timeout=MAKE_TIMEOUT):
            print("wait for attcs.startup")
            await self.attcs.startup()

            with self.assertRaises(RuntimeError):
                ret_val = await asyncio.gather(
                    self.attcs.slew_to_planet(
                        ATPtg.Planets.JUPITER,
                        slew_timeout=self.attcs_mock.slew_time * 2.0,
                    ),
                    self.attcs_mock.atmcs_wait_and_fault(1.0),
                    return_exceptions=True,
                )
                for val in ret_val:
                    if isinstance(val, Exception):
                        raise val
                    else:
                        print(f"ret_val: {val}")

    async def test_slew_toplanet_fail_atptg_fault(self):

        async with self.make_script(timeout=MAKE_TIMEOUT):
            print("wait for attcs.startup")
            await self.attcs.startup()

            with self.assertRaises(RuntimeError):
                ret_val = await asyncio.gather(
                    self.attcs.slew_to_planet(
                        ATPtg.Planets.JUPITER,
                        slew_timeout=self.attcs_mock.slew_time * 2.0,
                    ),
                    self.attcs_mock.atptg_wait_and_fault(1.0),
                    return_exceptions=True,
                )
                for val in ret_val:
                    if isinstance(val, Exception):
                        raise val
                    else:
                        print(f"ret_val: {val}")

    async def test_startup_shutdown(self):

        async with self.make_script(timeout=MAKE_TIMEOUT):
            # Testing when passing settings for all components

            settings = dict(
                zip(
                    self.attcs.components,
                    [f"setting4_{c}" for c in self.attcs.components],
                )
            )

            print("wait for attcs.startup 1")
            await self.attcs.startup(settings)

            for comp in settings:
                self.assertEqual(
                    self.attcs_mock.settings_to_apply[comp], settings[comp]
                )

            # Give remotes some time to update their data.
            await asyncio.sleep(self.attcs.fast_timeout)

            print("wait for attcs.shutdown 1")
            await asyncio.sleep(self.attcs.fast_timeout)
            await self.attcs.shutdown()

            # Testing when not passing settings for all components and only
            # atdome and ataos sent evt_settingVersions.
            # atdome sent a single label but ataos sends more then one.

            self.atdome.evt_settingVersions.set_put(
                recommendedSettingsLabels="setting4_atdome_set"
            )

            self.ataos.evt_settingVersions.set_put(
                recommendedSettingsLabels="setting4_ataos_set1,setting4_ataos2_set2"
            )

            # Give remotes some time to update their data.
            await asyncio.sleep(self.attcs.fast_timeout)

            print("wait for attcs.startup 2")
            await self.attcs.startup()

            for comp in self.attcs.components:
                if comp == "atdome":
                    self.assertEqual(
                        self.attcs_mock.settings_to_apply[comp], "setting4_atdome_set"
                    )
                elif comp == "ataos":
                    self.assertEqual(
                        self.attcs_mock.settings_to_apply[comp], "setting4_ataos_set1"
                    )
                else:
                    self.assertEqual(self.attcs_mock.settings_to_apply[comp], "")

            print("done")


if __name__ == "__main__":
    unittest.main()
