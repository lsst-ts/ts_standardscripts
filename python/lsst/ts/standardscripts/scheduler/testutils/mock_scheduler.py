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

__all__ = ["MockScheduler"]

import asyncio

from lsst.ts import salobj


class MockScheduler(salobj.Controller):
    """A simple Scheduler CSC simulator."""

    def __init__(
        self, index, initial_state=salobj.State.STANDBY, publish_initial_state=True
    ):
        super().__init__(name="Scheduler", index=index, do_callbacks=False)

        self.n_commands = dict(
            disable=0,
            enable=0,
            exitControl=0,
            standby=0,
            start=0,
        )

        self.running = False

        self.overrides = []
        self.snapshots = []
        self.abort_observations = []

        self.publish_initial_state = publish_initial_state

        self.valid_configuration_overrides = ["valid_test_config.yaml", ""]
        self.valid_snapshot = (
            "https://s3.cp.lsst.org/rubinobs-lfa-cp/Scheduler:2/"
            "Scheduler:2/2022/04/07/Scheduler:2_Scheduler:2_2022-04-08T09:56:57.726.p"
        )

        self.cmd_disable.callback = self.do_disable
        self.cmd_enable.callback = self.do_enable
        self.cmd_standby.callback = self.do_standby
        self.cmd_start.callback = self.do_start
        self.cmd_load.callback = self.do_load
        self.cmd_resume.callback = self.do_resume
        self.cmd_stop.callback = self.do_stop
        self.evt_summaryState.set(summaryState=initial_state)

    async def start(self):
        await super().start()
        if self.publish_initial_state:
            await self.evt_summaryState.write()
            await self.evt_largeFileObjectAvailable.set_write(url=self.valid_snapshot)

        self._heartbeat_task = asyncio.create_task(self.publish_heartbeat())

    async def publish_heartbeat(self):
        while self.isopen:
            await self.evt_heartbeat.write()
            await asyncio.sleep(1.0)

    async def do_disable(self, data):
        await self._do_change_state(
            cmd_name="disable",
            allowed_current_states={salobj.State.ENABLED},
            new_state=salobj.State.DISABLED,
        )

    async def do_enable(self, data):
        await self._do_change_state(
            cmd_name="enable",
            allowed_current_states={salobj.State.DISABLED},
            new_state=salobj.State.ENABLED,
        )

    async def do_standby(self, data):
        await self._do_change_state(
            cmd_name="standby",
            allowed_current_states={salobj.State.DISABLED, salobj.State.FAULT},
            new_state=salobj.State.STANDBY,
        )

    async def do_start(self, data):

        if data.configurationOverride not in self.valid_configuration_overrides:
            raise salobj.base.ExpectedError(
                f"Config file {data.configurationOverride} does not exist."
            )
        await self._do_change_state(
            cmd_name="start",
            allowed_current_states={salobj.State.STANDBY},
            new_state=salobj.State.DISABLED,
        )

        self.overrides.append(data.configurationOverride)

    async def do_load(self, data):
        assert self.evt_summaryState.data.summaryState == salobj.State.ENABLED
        assert not self.running
        assert data.uri == self.valid_snapshot

        self.snapshots.append(data.uri)

    async def do_resume(self, data):
        assert self.evt_summaryState.data.summaryState == salobj.State.ENABLED
        self.running = True

    async def do_stop(self, data):
        assert self.evt_summaryState.data.summaryState == salobj.State.ENABLED
        self.abort_observations.append(data.abort)
        self.running = False

    async def _do_change_state(self, cmd_name, allowed_current_states, new_state):

        current_state = self.evt_summaryState.data.summaryState
        if current_state not in allowed_current_states:
            raise salobj.base.ExpectedError(
                f"{cmd_name} not allowed in state {current_state!r}"
            )
        self.n_commands[cmd_name] += 1
        await self.evt_summaryState.set_write(summaryState=new_state)
