
import logging
import random
import unittest

import asynctest

from lsst.ts import salobj

from lsst.ts import standardscripts
from lsst.ts.standardscripts.base_group import BaseGroup

random.seed(47)  # for set_random_lsst_dds_domain

logging.basicConfig()

HB_TIMEOUT = 5  # Heartbeat timeout (sec)
MAKE_TIMEOUT = 60  # Timeout for make_script (sec)


class TestBaseGroup(standardscripts.BaseScriptTestCase, asynctest.TestCase):

    async def basic_make_script(self, index):
        self.basegroup = BaseGroup(components=["Test:1", "Test:2", "Test:3"])

        self.csc1 = salobj.TestCsc(index=1)
        self.csc2 = salobj.TestCsc(index=2)
        self.csc3 = salobj.TestCsc(index=3)

        return self.basegroup, self.csc1, self.csc2, self.csc3

    async def test_basic(self):

        async with self.make_script(timeout=MAKE_TIMEOUT):

            # Check that all CSCs go to enable State
            await self.basegroup.enable()

            for comp in self.basegroup.components:
                with self.subTest(msg=f"Check {comp} is enable",
                                  component=comp):
                    await getattr(self.basegroup, comp).evt_heartbeat.next(flush=True,
                                                                           timeout=HB_TIMEOUT)
                    ss = await self.basegroup.get_state(comp)
                    self.assertEqual(ss, salobj.State.ENABLED)

            # Check that all CSCs go to standby
            await self.basegroup.standby()

            for comp in self.basegroup.components:
                with self.subTest(msg=f"Check {comp} is in standby",
                                  component=comp):
                    await getattr(self.basegroup, comp).evt_heartbeat.next(flush=True,
                                                                           timeout=HB_TIMEOUT)
                    ss = await self.basegroup.get_state(comp)
                    self.assertEqual(ss, salobj.State.STANDBY)


if __name__ == "__main__":
    unittest.main()
