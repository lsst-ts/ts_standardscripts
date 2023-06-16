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

__all__ = ["BaseSchedulerTestCase"]

import contextlib
import random
import typing
import unittest

from lsst.ts import salobj
from lsst.ts.idl.enums.Script import ScriptState

from ...base_script_test_case import BaseScriptTestCase
from .mock_scheduler import MockScheduler

random.seed(47)  # for set_random_lsst_dds_partition_prefix


class BaseSchedulerTestCase(BaseScriptTestCase, unittest.IsolatedAsyncioTestCase):
    @contextlib.asynccontextmanager
    async def make_controller(
        self, initial_state: salobj.State, publish_initial_state: bool
    ):
        """Add a Test controller"""
        async with MockScheduler(
            index=1,
            initial_state=initial_state,
            publish_initial_state=publish_initial_state,
        ) as self.controller:
            yield

    def assert_run(
        self,
        expected_commands: typing.Dict[str, int],
        expected_overrides: typing.List[str],
        expected_script_state: ScriptState,
        expected_csc_state: salobj.State,
    ) -> None:
        for command in expected_commands:
            with self.subTest(
                f"successfull command execution {command}", command=command
            ):
                assert self.controller.n_commands[command] == expected_commands[command]

        assert len(self.controller.overrides) == len(
            expected_overrides
        ), f"Expected overrides, {len(expected_overrides)} got {len(self.controller.overrides)}."

        for expected_override, controller_override in zip(
            expected_overrides, self.controller.overrides
        ):
            with self.subTest(
                "expected overrides",
                expected_override=expected_override,
                controller_override=controller_override,
            ):
                assert expected_override == controller_override

        assert self.script.state.state == expected_script_state
        assert self.controller.evt_summaryState.data.summaryState == expected_csc_state

    def assert_loaded_snapshots(self, snapshots: typing.List[str]) -> None:
        assert len(self.controller.snapshots) == len(snapshots)
        for snapshot in snapshots:
            assert snapshot in self.controller.snapshots
