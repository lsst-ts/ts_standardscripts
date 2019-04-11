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

import asyncio
import logging
import os
import unittest

from lsst.ts import salobj
from lsst.ts import scriptqueue
from lsst.ts import standardscripts
from lsst.ts.standardscripts.auxtel.integration_tests import DomeTrajectoryMCS

import SALPY_Script

index_gen = salobj.index_generator()


class TestATCalSysTakeData(unittest.TestCase):
    def setUp(self):
        salobj.test_utils.set_random_lsst_dds_domain()
        self.processes = []

    def tearDown(self):
        for process in self.processes:
            if process.returncode is None:
                process.terminate()

    def test_integration(self):
        async def doit():
            print("*** Start ATMCS simulator")
            self.processes.append(await asyncio.create_subprocess_exec("run_atmcs_simulator.py"))
            print("*** Start ATDome in simulation mode")
            self.processes.append(await asyncio.create_subprocess_exec("run_atdome.py", "--simulate"))
            print("*** Start ATDomeTrajectory")
            self.processes.append(await asyncio.create_subprocess_exec("run_atdometrajectory.py"))

            print("*** Create DomeTrajectoryMCS script")
            script = DomeTrajectoryMCS(index=1)  # index is arbitrary
            script.log.setLevel(logging.INFO)
            script.log.addHandler(logging.StreamHandler())

            print("*** Wait for ATMCS to start up")
            data = await script.atmcs.evt_summaryState.next(flush=False, timeout=20)
            self.assertEqual(data.summaryState, salobj.State.STANDBY)
            print("*** Wait for ATDome to start up")
            data = await script.atdome.evt_summaryState.next(flush=False, timeout=20)
            self.assertEqual(data.summaryState, salobj.State.STANDBY)
            print("*** Wait for ATDomeTrajectory to start up")
            data = await script.atdometraj.evt_summaryState.next(flush=False, timeout=30)
            self.assertEqual(data.summaryState, salobj.State.STANDBY)

            print("*** Configure script")
            config_data = script.cmd_configure.DataType()
            config_data.config = ""
            config_id_data = salobj.CommandIdData(1, config_data)
            await script.do_configure(config_id_data)
            print("*** Run script")
            await script.do_run(None)
            self.assertEqual(script.state.state, scriptqueue.ScriptState.DONE)

        asyncio.get_event_loop().run_until_complete(doit())

    def test_executable(self):
        index = next(index_gen)

        script_name = "dometrajectory_mcs.py"
        scripts_dir = standardscripts.get_scripts_dir() / "auxtel" / "integration_tests"
        script_path = scripts_dir / script_name
        self.assertTrue(script_path.is_file())

        remote = salobj.Remote(SALPY_Script, index=index)

        async def doit():
            initial_path = os.environ["PATH"]
            try:
                os.environ["PATH"] = str(scripts_dir) + ":" + initial_path
                process = await asyncio.create_subprocess_exec(script_name, str(index))

                state = await remote.evt_state.next(flush=False, timeout=60)
                self.assertEqual(state.state, scriptqueue.ScriptState.UNCONFIGURED)

                process.terminate()
            finally:
                os.environ["PATH"] = initial_path

        asyncio.get_event_loop().run_until_complete(doit())


if __name__ == '__main__':
    unittest.main()
