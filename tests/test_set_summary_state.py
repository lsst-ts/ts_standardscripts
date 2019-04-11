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
import unittest
import os
import yaml

import numpy as np

from lsst.ts import salobj
from lsst.ts import scriptqueue
from lsst.ts.standardscripts import SetSummaryState, get_scripts_dir

import SALPY_Script
import SALPY_Test

np.random.seed(47)

index_gen = salobj.index_generator()


class TrivialController(salobj.Controller):
    def __init__(self, index, initial_state=salobj.State.STANDBY):
        super().__init__(SALPY_Test, index=index, do_callbacks=False)
        self.n_disable = 0
        self.n_enable = 0
        self.n_exitControl = 0
        self.n_standby = 0
        self.n_start = 0
        self.settings = []
        self.cmd_disable.callback = self.do_disable
        self.cmd_enable.callback = self.do_enable
        self.cmd_exitControl.callback = self.do_exitControl
        self.cmd_standby.callback = self.do_standby
        self.cmd_start.callback = self.do_start
        self.put_state(initial_state)

    def put_state(self, state):
        self.evt_summaryState.set_put(summaryState=state, force_output=True)

    def do_disable(self, id_data):
        self.n_disable += 1
        self.put_state(salobj.State.DISABLED)

    def do_enable(self, id_data):
        self.n_enable += 1
        self.put_state(salobj.State.ENABLED)

    def do_exitControl(self, id_data):
        self.n_exitControl += 1
        self.put_state(salobj.State.OFFLINE)

    def do_standby(self, id_data):
        self.n_standby += 1
        self.put_state(salobj.State.STANDBY)

    def do_start(self, id_data):
        self.n_start += 1
        self.settings.append(id_data.data.settingsToApply)
        self.put_state(salobj.State.DISABLED)


class Harness:
    def __init__(self):
        self.index = next(index_gen)
        self.test_index = next(index_gen)
        self.script = SetSummaryState(index=self.index)
        self.controllers = []

    def add_controller(self, initial_state=salobj.State.STANDBY):
        """Add a Test controller"""
        index = next(index_gen)
        self.controllers.append(TrivialController(index=index, initial_state=initial_state))


class TestSetSummaryState(unittest.TestCase):
    def setUp(self):
        salobj.test_utils.set_random_lsst_dds_domain()

    def test_configure_errors(self):
        """Test error handling in the configure method.
        """
        async def doit():
            harness = Harness()
            name_ind = f"Test:1"

            # Must specify at least one value
            with self.assertRaises(ValueError):
                await harness.script.configure(data=[])

            # too few (< 2) or too many values (> 3) values in an element
            with self.assertRaises(ValueError):
                await harness.script.configure(data=[[]])
            with self.assertRaises(ValueError):
                await harness.script.configure(data=[[name_ind]])
            with self.assertRaises(ValueError):
                await harness.script.configure(data=[[name_ind, "enabled", "", "no such field"]])

            # Invalid CSC name
            with self.assertRaises(ValueError):
                await harness.script.configure(data=[("Bad name:5", "enabled")])
            with self.assertRaises(ValueError):
                await harness.script.configure(data=[("Bad*name:5", "enabled")])
            with self.assertRaises(ValueError):
                await harness.script.configure(data=[("NoSuchCsc:5", "enabled")])

            # Invalid state
            with self.assertRaises(ValueError):
                await harness.script.configure(data=[(name_ind, "invalid_state")])
            with self.assertRaises(ValueError):
                await harness.script.configure(data=[(name_ind, "fault")])
            with self.assertRaises(ValueError):  # integer instead of string
                await harness.script.configure(data=[(name_ind, salobj.State.ENABLED)])

        asyncio.get_event_loop().run_until_complete(doit())

    def test_configure(self):
        """Test the configure method with a valid configuration.
        """
        async def doit():
            harness = Harness()
            harness.add_controller()
            harness.add_controller()
            # add a 3rd controller that has the same index as the first one
            harness.controllers.append(harness.controllers[0])
            state_enums = (salobj.State.ENABLED, salobj.State.DISABLED, salobj.State.STANDBY)
            state_names = [elt.name for elt in state_enums]
            settings_list = ("foo", None, "")

            data = []
            name_index_list = []
            for controller, state, settings in zip(harness.controllers, state_names, settings_list):
                index = controller.salinfo.index
                name_index = f"Test:{index}"
                if settings is None:
                    data.append((name_index, state))
                else:
                    data.append((name_index, state, settings))
                name_index_list.append(("Test", index))

            await harness.script.configure(data=data)

            # There are three controllers but two have the same index
            self.assertEqual(len(harness.script.remotes), 2)

            for i in range(len(data)):
                desired_settings = "" if settings_list[i] is None else settings_list[i]
                self.assertEqual(harness.script.nameind_state_settings[i],
                                 (name_index_list[i], state_enums[i], desired_settings))

        asyncio.get_event_loop().run_until_complete(doit())

    def test_do_run(self):
        """Set one remote to two states, including settings.

        Transition FAULT -standby> STANDBY -start> DISABLED -enable> ENABLED
        """
        async def doit():
            harness = Harness()
            harness.add_controller(initial_state=salobj.State.FAULT)
            test_index = harness.controllers[0].salinfo.index
            name_ind = f"Test:{test_index}"
            settings = "foo"

            data = (
                (name_ind, "standby"),
                (name_ind, "enabled", settings),
            )
            config_kwargs = dict(data=data)
            config_data = SALPY_Script.Script_command_configureC()
            config_data.config = yaml.safe_dump(config_kwargs)
            await harness.script.do_configure(id_data=salobj.CommandIdData(cmd_id=1, data=config_data))
            self.assertEqual(len(harness.controllers), 1)
            self.assertEqual(len(harness.script.remotes), 1)

            await harness.script.do_run(id_data=salobj.CommandIdData(cmd_id=2, data=None))
            controller = harness.controllers[0]
            self.assertEqual(controller.n_standby, 1)
            self.assertEqual(controller.n_start, 1)
            self.assertEqual(controller.n_enable, 1)
            self.assertEqual(controller.n_disable, 0)
            self.assertEqual(controller.n_exitControl, 0)
            self.assertEqual(len(controller.settings), 1)
            self.assertEqual(controller.settings[0], settings)
            self.assertEqual(harness.script.state.state, scriptqueue.ScriptState.DONE)

        asyncio.get_event_loop().run_until_complete(doit())

    def test_executable(self):
        index = next(index_gen)

        script_name = "set_summary_state.py"
        scripts_dir = get_scripts_dir()
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
