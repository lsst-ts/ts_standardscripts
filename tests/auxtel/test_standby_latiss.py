# This file is part of ts_standardscripts
#
# Developed for the LSST Data Management System.
# This product includes software developed by the LSST Project
# (https://www.lsst.org).
# See the COPYRIGHT file at the top-level directory of this distribution
# for details of code ownership.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License

import logging
import random
import unittest
import asynctest

from lsst.ts import salobj
from lsst.ts import standardscripts
from lsst.ts.standardscripts.auxtel import StandbyLATISS
from lsst.ts.observatory.control.mock import LATISSMock

random.seed(47)  # for set_random_lsst_dds_domain

logging.basicConfig()


class TestStandbyLATISS(standardscripts.BaseScriptTestCase, asynctest.TestCase):
    async def basic_make_script(self, index):
        self.script = StandbyLATISS(index=index)
        self.latiss_mock = LATISSMock()

        return (self.script, self.latiss_mock)

    async def test_run(self):
        async with self.make_script():
            await self.configure_script()

            await self.run_script()

            for comp in self.latiss_mock.components:
                with self.subTest(f"{comp} summary state", comp=comp):
                    self.assertEqual(
                        getattr(
                            self.latiss_mock, comp
                        ).evt_summaryState.data.summaryState,
                        salobj.State.STANDBY,
                    )

    async def test_executable(self):
        scripts_dir = standardscripts.get_scripts_dir()
        script_path = scripts_dir / "auxtel" / "standby_latiss.py"
        await self.check_executable(script_path)


if __name__ == "__main__":
    unittest.main()
