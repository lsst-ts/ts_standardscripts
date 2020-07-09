# This file is part of ts_standardscripts
#
# Developed for the LSST Telescope and Site Systems.
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

import unittest
import asynctest

from lsst.ts import salobj

from lsst.ts import standardscripts
from lsst.ts.standardscripts.maintel.integration_tests import CcwRotatorStressTest


class TestCcwRotatorStress(standardscripts.BaseScriptTestCase, asynctest.TestCase):
    async def basic_make_script(self, index):
        self.script = CcwRotatorStressTest(index=index)
        return (self.script,)

    async def test_configure(self):
        async with self.make_script():

            # Make sure it works with no parameters passed.
            await self.configure_script()

            self.assertEqual(self.script.n_rot_pos, 5)
            self.assertEqual(self.script.n_pos_repeat, 3)
            self.assertEqual(len(self.script.time_delays), 4)
            for delay in [1.0, 2.0, 5.0, 10.0]:
                self.assertTrue(delay in self.script.time_delays)

            # Make sure I can use n_rot_pos = 0
            await self.configure_script(n_rot_pos=0)
            self.assertEqual(self.script.n_rot_pos, 0)

            # Make sure I can run with no time delays
            await self.configure_script(time_delays=[])
            self.assertEqual(len(self.script.time_delays), 0)

            # Check some fail scenarios
            with self.assertRaises(salobj.ExpectedError):
                await self.configure_script(n_rot_pos=-1)

            # n_pos_repeat > 0
            with self.assertRaises(salobj.ExpectedError):
                await self.configure_script(n_rot_pos=5, n_pos_repeat=0)

            # First value is too low
            with self.assertRaises(salobj.ExpectedError):
                await self.configure_script(
                    n_rot_pos=5, n_pos_repeat=3, time_delays=[0.5, 1.0, 10.0]
                )

            # Last values is too high
            with self.assertRaises(salobj.ExpectedError):
                await self.configure_script(
                    n_rot_pos=5, n_pos_repeat=3, time_delays=[1.0, 10.0, 100.0]
                )

    async def test_executable(self):
        scripts_dir = standardscripts.get_scripts_dir()
        script_path = (
            scripts_dir / "maintel" / "integration_tests" / "ccw_rotator_stress.py"
        )
        await self.check_executable(script_path)


if __name__ == "__main__":
    unittest.main()
