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

import asyncio
import logging
import os
import random
import unittest
from unittest import mock

import pytest
from lsst.ts import salobj, standardscripts
from lsst.ts.xml.enums.Script import ScriptState
from lsst.ts.xml.enums.Watcher import AlarmSeverity

random.seed(47)  # for set_random_lsst_dds_partition_prefix

logging.basicConfig()


class TrivialController(salobj.Controller):
    def __init__(self, index, initial_state=salobj.State.STANDBY):
        super().__init__(name="Test", index=index, do_callbacks=False)
        self.n_disable = 0
        self.n_enable = 0
        self.n_exitControl = 0
        self.n_standby = 0
        self.n_start = 0
        self.overrides = []
        self.cmd_disable.callback = self.do_disable
        self.cmd_enable.callback = self.do_enable
        self.cmd_exitControl.callback = self.do_exitControl
        self.cmd_standby.callback = self.do_standby
        self.cmd_start.callback = self.do_start
        self.evt_summaryState.set(summaryState=initial_state)

    async def start(self):
        await super().start()
        await self.evt_summaryState.write()

    async def do_disable(self, data):
        self.n_disable += 1
        await self.evt_summaryState.set_write(summaryState=salobj.State.DISABLED)

    async def do_enable(self, data):
        self.n_enable += 1
        await self.evt_summaryState.set_write(summaryState=salobj.State.ENABLED)

    async def do_exitControl(self, data):
        self.n_exitControl += 1
        await self.evt_summaryState.set_write(summaryState=salobj.State.OFFLINE)

    async def do_standby(self, data):
        self.n_standby += 1
        await self.evt_summaryState.set_write(summaryState=salobj.State.STANDBY)

    async def do_start(self, data):
        self.n_start += 1
        self.overrides.append(data.configurationOverride)
        await self.evt_summaryState.set_write(summaryState=salobj.State.DISABLED)


class TestSetSummaryState(
    standardscripts.BaseScriptTestCase, unittest.IsolatedAsyncioTestCase
):

    @classmethod
    def setUpClass(cls) -> None:
        os.environ["LSST_SITE"] = "test"

    async def basic_make_script(self, index):
        self.script = standardscripts.SetSummaryState(index=index)

        self.controllers = []

        return [self.script]

    async def add_test_cscs(self, initial_state=salobj.State.STANDBY):
        """Add a Test controller"""
        index = self.next_index()

        controller = salobj.TestCsc(index=index, initial_state=initial_state)
        await controller.start_task
        self.controllers.append(controller)

    async def add_controller(self, initial_state=salobj.State.STANDBY):
        """Add a Test controller"""
        index = self.next_index()

        controller = TrivialController(index=index, initial_state=initial_state)
        await controller.start_task
        self.controllers.append(controller)

    async def close(self):
        await asyncio.gather(*[controller.close() for controller in self.controllers])

    async def test_configure_errors(self):
        """Test error handling in the do_configure method."""
        name_ind = "Test:1"
        for bad_data in (
            "[]",  # need at least one tuple
            "[[]]",  # tuple has 0 items; need 2 or 3
            f'[["{name_ind}"]]',  # tuple has 1 item; need 2 or 3
            # tuple has 4 items; need 2 or 3:
            f'[["{name_ind}", "enabled", "", "4th field not allowed"]]',
            '[("invalid csc name:5", "enabled")]',  # bad CSC name format
            '[("invalid*csc*name:5", "enabled")]',  # bad CSC name format
            '[("no_such_CSC:5", "enabled")]',  # no such CSC
            '[(name_ind, "invalid_state")]',  # no such state
            '[(name_ind, "fault")]',  # fault state is not supported
            "[(name_ind, 1)]",  # integer states are not supported
        ):
            bad_config = dict(data=bad_data)
            with self.subTest(bad_config=bad_config):
                async with self.make_script():
                    with pytest.raises(salobj.ExpectedError):
                        await self.configure_script(**bad_config)

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
            override_list = ("foo", None, "")

            data = []
            name_index_list = []
            for controller, state, override in zip(
                self.controllers, state_names, override_list
            ):
                index = controller.salinfo.index
                name_index = f"Test:{index}"
                if override is None:
                    data.append((name_index, state))
                else:
                    data.append((name_index, state, override))
                name_index_list.append(("Test", index))

            await self.configure_script(data=data)

            # There are three controllers but two have the same index
            assert len(self.script.remotes) == 2

            for i in range(len(data)):
                desired_override = "" if override_list[i] is None else override_list[i]
                assert self.script.nameind_state_override[i] == (
                    name_index_list[i],
                    state_enums[i],
                    desired_override,
                )

    async def test_do_run(self):
        """Set one remote to two states, including overrides.

        Transition FAULT -standby> STANDBY -start> DISABLED -enable> ENABLED
        """
        async with self.make_script():
            await self.add_controller(initial_state=salobj.State.FAULT)
            test_index = self.controllers[0].salinfo.index
            name_ind = f"Test:{test_index}"
            override = "foo"

            data = ((name_ind, "standby"), (name_ind, "enabled", override))
            await self.configure_script(data=data)
            assert len(self.controllers) == 1
            assert len(self.script.remotes) == 1

            await self.run_script()
            controller = self.controllers[0]
            assert controller.n_standby == 1
            assert controller.n_start == 1
            assert controller.n_enable == 1
            assert controller.n_disable == 0
            assert controller.n_exitControl == 0
            assert len(controller.overrides) == 1
            assert controller.overrides[0] == override
            assert self.script.state.state == ScriptState.DONE

    async def test_executable(self):
        scripts_dir = standardscripts.get_scripts_dir()
        script_path = scripts_dir / "set_summary_state.py"
        await self.check_executable(script_path)

    async def run_configure_wildcard_index_test(self):
        """Test the configure method with a wildcard (*) index.

        This simulates the discovery of multiple instances of a CSC
        and setting their states.
        """
        async with self.make_script(verbose=True):
            await self.add_test_cscs(initial_state=salobj.State.OFFLINE)
            await self.add_test_cscs(initial_state=salobj.State.STANDBY)
            await self.add_test_cscs(initial_state=salobj.State.STANDBY)
            await self.add_test_cscs(initial_state=salobj.State.DISABLED)
            await self.add_test_cscs(initial_state=salobj.State.ENABLED)

            name_ind = [("Test:*", "ENABLED")]

            await self.configure_script(data=name_ind)

            # Assert that all controllers are present (4 total)
            assert (
                len(self.controllers) == 5
            ), f"Expected 4 controllers, found {len(self.controllers)}"

            # Assert that the remotes (excluding OFFLINE controllers)
            # are present (4 remotes)
            assert (
                len(self.script.remotes) == 4
            ), f"Expected 4 remotes, found {len(self.script.remotes)}"

            await self.run_script()

            # Assert that all controllers (except OFFLINE) have transitioned
            # to ENABLED
            for controller in self.controllers:
                name_index = (controller.salinfo.name, controller.salinfo.index)

                if (
                    controller.evt_summaryState.data.summaryState
                    != salobj.State.OFFLINE
                ):
                    assert (
                        controller.evt_summaryState.data.summaryState
                        == salobj.State.ENABLED
                    ), (
                        f"Controller {name_index} did not transition to ENABLED. "
                        f"Current state: {controller.evt_summaryState.data.summaryState}"
                    )
                else:
                    # Verify that OFFLINE controllers remain OFFLINE
                    assert (
                        controller.evt_summaryState.data.summaryState
                        == salobj.State.OFFLINE
                    ), (
                        f"Controller {name_index} was expected to remain OFFLINE but is in state "
                        f"{controller.evt_summaryState.data.summaryState}"
                    )

    async def test_configure_wildcard_index_local_fallback(self):
        """Test the configure method with a wildcard (*) index
        using the local fallback for wildcard handling.
        """
        from lsst.ts.standardscripts.utils import (
            WildcardIndexError as LocalWildcardIndexError,
        )
        from lsst.ts.standardscripts.utils import (
            name_to_name_index as local_name_to_name_index,
        )

        with mock.patch(
            "lsst.ts.standardscripts.set_summary_state.name_to_name_index",
            local_name_to_name_index,
        ), mock.patch(
            "lsst.ts.standardscripts.set_summary_state.WildcardIndexError",
            LocalWildcardIndexError,
        ):
            await self.run_configure_wildcard_index_test()

    async def test_configure_wildcard_index_salobj(self):
        """Test the configure method with ts_salobj's native wildcard
        handling."""
        try:
            # Check if WildcardIndexError exists in ts_salobj
            from lsst.ts.salobj import WildcardIndexError  # noqa: F401
        except ImportError:
            pytest.skip("ts_salobj does not yet support WildcardIndexError")

        await self.run_configure_wildcard_index_test()

    async def test_mute_alarms_when_offline(self):
        """Test that alarms are muted when CSCs are set to OFFLINE with
        mute_alarms=True."""
        async with self.make_script():
            self.script.watcher = unittest.mock.AsyncMock()

            await self.add_test_cscs(initial_state=salobj.State.ENABLED)
            await self.add_test_cscs(initial_state=salobj.State.ENABLED)
            await self.add_test_cscs(initial_state=salobj.State.ENABLED)
            await self.add_test_cscs(initial_state=salobj.State.ENABLED)

            controllers = self.controllers
            csc_info = []
            for controller in controllers:
                name = controller.salinfo.name
                index = controller.salinfo.index
                name_ind = f"{name}:{index}"
                csc_info.append((controller, name, index, name_ind))

            offline_cscs = [csc_info[0][0], csc_info[2][0]]

            config_data = []
            for controller, name, index, name_ind in csc_info:
                if controller in offline_cscs:
                    config_data.append((name_ind, "OFFLINE"))
                else:
                    config_data.append((name_ind, "STANDBY"))

            await self.configure_script(
                data=config_data, mute_alarms=True, mute_duration=31.0
            )

            await self.run_script()

            expected_mute_calls = [
                mock.call(
                    name=rf"^(Enabled|Heartbeat)\.{name}:{index}",
                    duration=1860.0,  # mute_duration * 60 secs`
                    severity=AlarmSeverity.CRITICAL,
                    mutedBy="set_summary_state script",
                )
                for controller, name, index, name_ind in csc_info
                if controller in offline_cscs
            ]

            self.script.watcher.cmd_mute.set_start.assert_has_awaits(
                expected_mute_calls, any_order=True
            )

            expected_mute_calls_count = len(offline_cscs)
            actual_mute_calls_count = self.script.watcher.cmd_mute.set_start.await_count
            self.assertEqual(
                actual_mute_calls_count,
                expected_mute_calls_count,
                f"Expected {expected_mute_calls_count} mute command(s), but got {actual_mute_calls_count}",
            )

            # Verify that CSCs have transitioned to the correct states
            for controller, name, index, name_ind in csc_info:
                expected_state = (
                    salobj.State.OFFLINE
                    if controller in offline_cscs
                    else salobj.State.STANDBY
                )
                actual_state = controller.evt_summaryState.data.summaryState
                self.assertEqual(
                    actual_state,
                    expected_state,
                    f"CSC {name_ind} expected to be in state {expected_state.name}, but found "
                    f"{actual_state.name}",
                )


if __name__ == "__main__":
    unittest.main()
