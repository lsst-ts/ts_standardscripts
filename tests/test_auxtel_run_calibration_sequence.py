# This file is part of ts_externalscripts
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
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

import unittest

import pytest
from lsst.ts import salobj
from lsst.ts.auxtel.standardscripts import get_scripts_dir
from lsst.ts.auxtel.standardscripts.calibrations import RunCalibrationSequence
from lsst.ts.observatory.control.auxtel.atcalsys import ATCalsys, ATCalsysUsages
from lsst.ts.observatory.control.auxtel.latiss import LATISS, LATISSUsages
from lsst.ts.standardscripts import BaseScriptTestCase


class TestRunCalibrationSequence(BaseScriptTestCase, unittest.IsolatedAsyncioTestCase):

    async def basic_make_script(self, index):

        self.script = RunCalibrationSequence(index=index)

        self.script.latiss = LATISS(
            domain=self.script.domain,
            log=self.script.log,
            intended_usage=LATISSUsages.DryTest,
        )
        self.script.atcalsys = ATCalsys(
            domain=self.script.domain,
            log=self.script.log,
            intended_usage=ATCalsysUsages.DryTest,
        )

        return (self.script,)

    async def test_config(self):
        async with self.make_script():
            await self.configure_script(sequence_name="at_whitelight_r")
            assert self.script.sequence_name == "at_whitelight_r"

    async def test_config_fail_if_empty(self):
        async with self.make_script():
            with pytest.raises(salobj.ExpectedError):
                await self.configure_script()

    async def test_executable(self):
        scripts_dir = get_scripts_dir()
        script_path = scripts_dir / "calibrations" / "run_calibration_sequence.py"
        await self.check_executable(script_path)
