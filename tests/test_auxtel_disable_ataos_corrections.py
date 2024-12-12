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
# along with this program. If not, see <https://www.gnu.org/licenses/>.

import logging
import random
import unittest

from lsst.ts import standardscripts
from lsst.ts.observatory.control.auxtel.atcs import ATCS, ATCSUsages
from lsst.ts.observatory.control.mock import ATCSMock
from lsst.ts.standardscripts.auxtel import DisableATAOSCorrections

random.seed(47)  # for set_random_lsst_dds_partition_prefix

logging.basicConfig()


class TestDisableATAOSCorrections(
    standardscripts.BaseScriptTestCase, unittest.IsolatedAsyncioTestCase
):

    async def basic_make_script(self, index):
        self.script = DisableATAOSCorrections(index=index)
        self.atcs_mock = ATCSMock()

        self.script.atcs = ATCS(
            domain=self.script.domain,
            intended_usage=ATCSUsages.All,
            log=self.script.log,
        )

        self.script.atcs.disable_checks_for_components = unittest.mock.Mock()

        return (self.script, self.atcs_mock)

    async def test_configure_ignore(self):
        async with self.make_script():
            components = ["atmcs", "notcomp", "athexapod"]
            await self.configure_script(ignore=components)

            self.script.atcs.disable_checks_for_components.assert_called_once_with(
                components=components
            )

    async def test_configure_ignore_fail(self):
        # Test the ignore_fail configuration.
        async with self.make_script():
            # Test default value for ignore_fail
            await self.configure_script()
            assert self.script.ignore_fail
            # Test configuring ingore_fail value
            config_values = [True, False]
            for test_value in config_values:
                await self.configure_script(ignore_fail=test_value)
                assert self.script.ignore_fail == test_value

    async def test_run(self):
        async with self.make_script():
            await self.configure_script()
            await self.script.atcs.enable()

            await self.run_script()
            # TODO: Find a way to get the list of corrections for ATAOS to
            #       avoid hardcoding.
            ataos_corrections = [
                "m1",
                "m2",
                "hexapod",
                "focus",
                "atspectrograph",
                "moveWhileExposing",
            ]
            # Check that all corrections are disabled.
            for correction in ataos_corrections:
                assert not getattr(
                    self.atcs_mock.ataos.evt_correctionEnabled.data, correction
                )

    async def test_executable(self):
        scripts_dir = standardscripts.get_scripts_dir()
        script_path = scripts_dir / "auxtel" / "disable_ataos_corrections.py"
        await self.check_executable(script_path)


if __name__ == "__main__":
    unittest.main()
