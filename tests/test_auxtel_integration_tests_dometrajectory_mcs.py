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

import asyncio
import logging
import random
import unittest

from lsst.ts import salobj
from lsst.ts import standardscripts
from lsst.ts.standardscripts.auxtel.integration_tests import DomeTrajectoryMCS

# Long enough to perform any reasonable operation
# including starting a CSC, loading a script,
# or slewing the dome and telescope (sec)
STD_TIMEOUT = 240

random.seed(47)  # for set_random_lsst_dds_partition_prefix

logging.basicConfig()


class DomeTrajectoryMCSTestCase(
    standardscripts.BaseScriptTestCase, unittest.IsolatedAsyncioTestCase
):
    def setUp(self):
        self.processes = []

    def tearDown(self):
        for process in self.processes:
            if process.returncode is None:
                process.terminate()

    async def basic_make_script(self, index):

        print("*** Wait for DomeTrajectoryMCS script to start")
        self.script = DomeTrajectoryMCS(index=index)
        await asyncio.wait_for(self.script.start_task, timeout=STD_TIMEOUT)

        print("*** Start ATDome in simulation mode")
        async with salobj.Domain() as d:
            remote = salobj.Remote(
                d, "ATDome", include=["heartbeat", "summaryState"], readonly=True
            )

            await remote.start_task

            self.processes.append(
                await asyncio.create_subprocess_exec("run_atdome.py", "--simulate")
            )

            await remote.evt_heartbeat.next(flush=True, timeout=STD_TIMEOUT / 4)

            print("*** got heartbeat from ATDome")

            ss = salobj.State(
                (
                    await remote.evt_summaryState.aget(timeout=STD_TIMEOUT / 4)
                ).summaryState
            )

            print(f"*** ATDome in {ss!r}")

            await remote.close()

            remote = salobj.Remote(
                d, "ATMCS", include=["heartbeat", "summaryState"], readonly=True
            )

            await remote.start_task

            print("*** Start ATMCS simulator")
            self.processes.append(
                await asyncio.create_subprocess_exec("run_atmcs_simulator.py")
            )

            await remote.evt_heartbeat.next(flush=True, timeout=STD_TIMEOUT / 4)

            print("*** got heartbeat from ATMCS")

            ss = salobj.State(
                (
                    await remote.evt_summaryState.aget(timeout=STD_TIMEOUT / 4)
                ).summaryState
            )

            print(f"*** ATMCS in {ss!r}")

            await remote.close()

            remote = salobj.Remote(
                d,
                "ATDomeTrajectory",
                include=["heartbeat", "summaryState"],
                readonly=True,
            )

            await remote.start_task

            print("*** Start ATDomeTrajectory")
            self.processes.append(
                await asyncio.create_subprocess_exec("run_atdometrajectory.py")
            )

            await remote.evt_heartbeat.next(flush=True, timeout=STD_TIMEOUT / 4)

            print("*** got heartbeat from ATDomeTrajectory")

            ss = salobj.State(
                (
                    await remote.evt_summaryState.aget(timeout=STD_TIMEOUT / 4)
                ).summaryState
            )

            print(f"*** ATDomeTrajectory in {ss!r}")

            await remote.close()

        print("*** Wait for ATMCS to start up")
        data = await self.script.atmcs.evt_summaryState.aget(timeout=STD_TIMEOUT / 4)
        self.assertEqual(data.summaryState, salobj.State.STANDBY)
        print("*** Wait for ATDome to start up")
        data = await self.script.atdome.evt_summaryState.aget(timeout=STD_TIMEOUT / 4)
        self.assertEqual(data.summaryState, salobj.State.STANDBY)
        print("*** Wait for ATDomeTrajectory to start up")
        data = await self.script.atdometraj.evt_summaryState.aget(
            timeout=STD_TIMEOUT / 4
        )
        self.assertEqual(data.summaryState, salobj.State.STANDBY)

        return [self.script]

    async def test_integration(self):
        async with self.make_script(timeout=STD_TIMEOUT):
            print("*** Configure and run script")
            await self.configure_script()
            await self.run_script()

    async def test_executable(self):
        scripts_dir = standardscripts.get_scripts_dir()
        script_path = (
            scripts_dir / "auxtel" / "integration_tests" / "dometrajectory_mcs.py"
        )
        await self.check_executable(script_path)


if __name__ == "__main__":
    unittest.main()
