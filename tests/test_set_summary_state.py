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

import asynctest

from lsst.ts import salobj
from lsst.ts.idl.enums.Script import ScriptState
from lsst.ts import standardscripts

random.seed(47)  # for set_random_lsst_dds_domain

logging.basicConfig()


class TrivialController(salobj.Controller):
    def __init__(self, index, initial_state=salobj.State.STANDBY):
        super().__init__(name="Test", index=index, do_callbacks=False)
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

    def do_disable(self, data):
        self.n_disable += 1
        self.put_state(salobj.State.DISABLED)

    def do_enable(self, data):
        self.n_enable += 1
        self.put_state(salobj.State.ENABLED)

    def do_exitControl(self, data):
        self.n_exitControl += 1
        self.put_state(salobj.State.OFFLINE)

    def do_standby(self, data):
        self.n_standby += 1
        self.put_state(salobj.State.STANDBY)

    def do_start(self, data):
        self.n_start += 1
        self.settings.append(data.settingsToApply)
        self.put_state(salobj.State.DISABLED)


class TestSetSummaryState(standardscripts.BaseScriptTestCase, asynctest.TestCase):
    async def basic_make_script(self, index):
        self.script = standardscripts.SetSummaryState(index=index)
        self.controllers = []
        return [self.script]

    async def add_controller(self, initial_state=salobj.State.STANDBY):
        """Add a Test controller"""
        index = self.next_index()

        controller = TrivialController(index=index, initial_state=initial_state)
        await controller.start_task
        self.controllers.append(controller)

    async def close(self):
        await asyncio.gather(*[controller.close() for controller in self.controllers])

    async def test_configure_errors(self):
        """Test error handling in the do_configure method.
        """
        async with self.make_script():
            name_ind = "Test:1"
            config_data = self.script.cmd_configure.DataType()
            for bad_config in (
                "data: []",  # need at least one tuple
                "data: [[]]",  # tuple has 0 values; need 2 or 3
                f'data: [["{name_ind}"]]',  # tuple has 1 item; need 2 or 3
                # tuple has 4 items; need 2 or 3
                f'data: [["{name_ind}", "enabled", "", "4th field not allowed"]]',
                '[("invalid csc name:5", "enabled")]',  # bad CSC name format
                '[("invalid*csc*name:5", "enabled")]',  # bad CSC name format
                '[("no_such_CSC:5", "enabled")]',  # no such CSC
                '[(name_ind, "invalid_state")]',  # no such state
                '[(name_ind, "fault")]',  # fault state is not supported
                "[(name_ind, 1)]",  # integer states are not supported
            ):
                with self.subTest(bad_config=bad_config):
                    config_data.config = bad_config
                    with self.assertRaises(salobj.ExpectedError):
                        await self.script.do_configure(config_data)

    async def test_configure_good(self):
        """Test the configure method with a valid configuration.

        Also exercise verbose=True for make_script.
        """
        async with self.make_script(verbose=True):
            await self.add_controller()
            await self.add_controller()
            # add a 3rd controller that has the same index as the first one
            self.controllers.append(self.controllers[0])
            state_enums = (
                salobj.State.ENABLED,
                salobj.State.DISABLED,
                salobj.State.STANDBY,
            )
            state_names = [elt.name for elt in state_enums]
            settings_list = ("foo", None, "")

            data = []
            name_index_list = []
            for controller, state, settings in zip(
                self.controllers, state_names, settings_list
            ):
                index = controller.salinfo.index
                name_index = f"Test:{index}"
                if settings is None:
                    data.append((name_index, state))
                else:
                    data.append((name_index, state, settings))
                name_index_list.append(("Test", index))

            await self.configure_script(data=data)

            # There are three controllers but two have the same index
            self.assertEqual(len(self.script.remotes), 2)

            for i in range(len(data)):
                desired_settings = "" if settings_list[i] is None else settings_list[i]
                self.assertEqual(
                    self.script.nameind_state_settings[i],
                    (name_index_list[i], state_enums[i], desired_settings),
                )

    async def test_do_run(self):
        """Set one remote to two states, including settings.

        Transition FAULT -standby> STANDBY -start> DISABLED -enable> ENABLED
        """
        async with self.make_script():
            await self.add_controller(initial_state=salobj.State.FAULT)
            test_index = self.controllers[0].salinfo.index
            name_ind = f"Test:{test_index}"
            settings = "foo"

            data = ((name_ind, "standby"), (name_ind, "enabled", settings))
            await self.configure_script(data=data)
            self.assertEqual(len(self.controllers), 1)
            self.assertEqual(len(self.script.remotes), 1)

            await self.run_script()
            controller = self.controllers[0]
            self.assertEqual(controller.n_standby, 1)
            self.assertEqual(controller.n_start, 1)
            self.assertEqual(controller.n_enable, 1)
            self.assertEqual(controller.n_disable, 0)
            self.assertEqual(controller.n_exitControl, 0)
            self.assertEqual(len(controller.settings), 1)
            self.assertEqual(controller.settings[0], settings)
            self.assertEqual(self.script.state.state, ScriptState.DONE)

    async def test_executable(self):
        scripts_dir = standardscripts.get_scripts_dir()
        script_path = scripts_dir / "set_summary_state.py"
        await self.check_executable(script_path)


if __name__ == "__main__":
    unittest.main()
