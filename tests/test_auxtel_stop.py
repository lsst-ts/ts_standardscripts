# This file is part of ts_auxtel_standardscripts
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

import functools
import logging
import random
import unittest

from lsst.ts import salobj, standardscripts
from lsst.ts.auxtel.standardscripts import Stop, get_scripts_dir

random.seed(47)  # for set_random_lsst_dds_partition_prefix

logging.basicConfig()


class TestStartup(standardscripts.BaseScriptTestCase, unittest.IsolatedAsyncioTestCase):
    async def basic_make_script(self, index):
        self.script = Stop(index=index)

        # A dict of name: number of calls
        # where name is {controller_name_index}.{command_name}
        self.num_calls = dict()

        # A dict of name_index: numer of calls
        # where name_index means the SAL component name and index
        # in the form name[:index] and [:index] is only wanted for
        # indexed SAL components.
        self.controllers = dict()

        for name_index in ("ATDome", "ATDomeTrajectory", "ATPtg", "ATMCS"):
            name, index = salobj.name_to_name_index(name_index)
            controller = salobj.Controller(name=name, index=index)
            self.controllers[name_index] = controller
            await controller.start_task
            await controller.evt_summaryState.set_write(
                summaryState=salobj.State.ENABLED
            )
            for command_name in controller.salinfo.command_names:
                name = f"{name_index}.{command_name}"
                self.num_calls[name] = 0
                command = getattr(controller, f"cmd_{command_name}")
                command.callback = functools.partial(self.callback, name)

        return (self.script,) + tuple(self.controllers.values())

    def callback(self, name, data):
        self.num_calls[name] += 1

    async def test_run(self):
        async with self.make_script():
            await self.configure_script()
            await self.run_script()

        for name in (
            "ATDome.stopMotion",
            "ATDomeTrajectory.disable",
            "ATPtg.stopTracking",
            "ATMCS.stopTracking",
        ):
            assert self.num_calls[name] == 1

    async def test_executable(self):
        scripts_dir = get_scripts_dir()
        script_path = scripts_dir / "stop.py"
        await self.check_executable(script_path)


if __name__ == "__main__":
    unittest.main()
