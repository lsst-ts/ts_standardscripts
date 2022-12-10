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

import logging
import random
import unittest

from lsst.ts import standardscripts
from lsst.ts.standardscripts.auxtel.prepare_for import PrepareForOnSky
from lsst.ts.observatory.control.mock import ATCSMock

random.seed(47)  # for set_random_lsst_dds_partition_prefix

logging.basicConfig()


class TestPrepareForOnSky(
    standardscripts.BaseScriptTestCase, unittest.IsolatedAsyncioTestCase
):
    async def basic_make_script(self, index):
        self.script = PrepareForOnSky(index=index)
        self.atcs_mock = ATCSMock()

        return (self.script, self.atcs_mock)

    async def test_configure(self):
        async with self.make_script():
            # works with no configuration
            await self.configure_script()

        async with self.make_script():
            await self.configure_script(ignore=["atpneumatics", "ataos"])

            assert not self.script.attcs.check.atpneumatics
            assert not self.script.attcs.check.ataos

        async with self.make_script():
            with self.assertLogs(self.script.log, level=logging.WARNING) as script_logs:
                await self.configure_script(ignore=["nonono"])

            expected_warning_msg = (
                f"WARNING:Script:Component nonono not in CSC Group. "
                f"Must be one of {self.script.attcs.components_attr}. Ignoring."
            )

            assert expected_warning_msg in script_logs.output

    async def test_executable(self):
        scripts_dir = standardscripts.get_scripts_dir()
        script_path = scripts_dir / "auxtel" / "prepare_for" / "onsky.py"
        await self.check_executable(script_path)


if __name__ == "__main__":
    unittest.main()
