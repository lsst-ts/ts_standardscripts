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

import random
import unittest

from lsst.ts import standardscripts
from lsst.ts.maintel.standardscripts.prepare_for import PrepareForAlign

random.seed(47)  # for set_random_lsst_dds_partition_prefix


class TestPrepareForAlign(
    standardscripts.BaseScriptTestCase, unittest.IsolatedAsyncioTestCase
):
    async def basic_make_script(self, index):
        self.script = PrepareForAlign(index=index)

        return (self.script,)

    async def test_configure(self):
        async with self.make_script():
            # Check it work with no configuration
            await self.configure_script()

        async with self.make_script():
            tel_align_az = 0
            tel_align_el = 70
            tel_align_rot = 0

            await self.configure_script(
                tel_align_az=tel_align_az,
                tel_align_el=tel_align_el,
                tel_align_rot=tel_align_rot,
            )

            assert self.script.tel_align_az == tel_align_az
            assert self.script.tel_align_el == tel_align_el
            assert self.script.tel_align_rot == tel_align_rot

    async def test_executable(self):
        scripts_dir = standardscripts.get_scripts_dir()
        script_path = scripts_dir / "maintel" / "prepare_for" / "align.py"
        await self.check_executable(script_path)


if __name__ == "__main__":
    unittest.main()
