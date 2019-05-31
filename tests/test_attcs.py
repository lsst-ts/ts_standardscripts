from lsst.ts.standardscripts.auxtel.attcs import ATTCS
import unittest
import asyncio
from lsst.ts import salobj
from lsst.ts.salobj import test_utils
from math import isclose

import SALPY_ATMCS
import SALPY_ATAOS
import SALPY_ATHexapod
import SALPY_ATPneumatics
import SALPY_ATPtg
# import SALPY_ATDome
# import SALPY_ATDomeTrajectory

index_gen = salobj.index_generator()


class Harness:
    def __init__(self):
        self.index = next(index_gen)
        self.test_index = next(index_gen)
        test_utils.set_random_lsst_dds_domain()

        ATMCSRem = salobj.Remote(SALPY_ATMCS)
        ATAOSRem = salobj.Remote(SALPY_ATAOS)
        ATPneumaticsRem = salobj.Remote(SALPY_ATPneumatics)
        ATHexapodRem = salobj.Remote(SALPY_ATHexapod)
        ATDomeRem = None  # TODO: Add these later
        ATDomeTrajRem = None

        self.attcs = ATTCS(ATMCSRem, ATAOSRem, ATPneumaticsRem,
                        ATHexapodRem, ATDomeRem, ATDomeTrajRem)

        self.atmcs = salobj.Controller(SALPY_ATMCS)
        self.atptg = salobj.Controller(SALPY_ATPtg)
        self.atptg.cmd_raDecTarget.callback = self.cmd_raDecTarget_callback

    async def cmd_raDecTarget_callback(self, id_data):
        """fake slew waits 5 seconds, then reports all axes 
           in position. Doesdoes not simulate the actual slew."""
        asyncio.sleep(5)
        self.atmcs.evt_allAxesInPosition.put()


class testATTCS(unittest.TestCase):        

    def test_slew(self):
        test_utils.set_random_lsst_dds_domain()

        async def runtest():
            harness = Harness()
            harness.attcs.slew(45., 45.)
            slewResult = await harness.attcs.atmcs.tel_mountEncoders.next(flush=False, timeout=0)
            assert isclose(slewResult.elevationCalculatedAngle, 45.0, rel_tol=0.03)
            assert isclose(slewResult.azimuthCalculatedAngle, 45.0, rel_tol=0.03)
        asyncio.get_event_loop().run_until_complete(runtest())

    def test_fails_when_atptg_faults(self):
        pass

    def test_fails_when_atmcs_faults(self):
        pass


if __name__ == '__main__':
    unittest.main()
