from .attcs import ATTCS
import unittest
import asyncio
from lsst.ts.salobj import test_utils
from math import isclose


class testATTCS(unittest.TestCase):

    def setup(self):
        self.attcs = ATTCS()

    def test_slew(self):
        test_utils.set_random_lsst_dds_domain()

        async def runtest():
            self.attcs.slew(45., 45.)
            slewResult = await self.attcs.atmcs.tel_mountEncoders.next(flush=False, timeout=1)
            assert isclose(slewResult.elevationCalculatedAngle, 45.0, rel_tol=0.03)
            assert isclose(slewResult.azimuthCalculatedAngle, 45.0, rel_tol=0.03)
        asyncio.get_event_loop().run_until_complete(runtest())

