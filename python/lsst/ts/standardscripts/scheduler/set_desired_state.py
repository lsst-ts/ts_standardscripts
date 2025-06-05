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

__all__ = ["SetDesiredState"]

import asyncio
import types
import typing

from lsst.ts import salobj
from lsst.ts.xml.enums.Scheduler import SalIndex


class SetDesiredState(salobj.BaseScript):
    """A base script that implements setting the desired state for the
    Scheduler.

    Parameters
    ----------
    index : `int`
        Index of Script SAL component.
    descr : `str`
        Script description.
    scheduler_index : `int`
        Index of the Scheduler to enable.
    """

    def __init__(
        self,
        index: int,
        descr: str,
        scheduler_index: SalIndex,
        desired_state: salobj.State,
    ) -> None:
        super().__init__(index=index, descr=descr)

        self.scheduler_remote = salobj.Remote(
            domain=self.domain,
            name="Scheduler",
            index=scheduler_index,
            include=["summaryState", "heartbeat"],
        )

        self.desired_state = desired_state

        self.timeout_start = 30.0

        self.configuration = ""

        self._state_transition_methods_to_try = (
            self._handle_csc_in_standby,
            self._handle_csc_in_disabled_or_fault,
            self._handle_csc_in_enabled,
        )

    @classmethod
    def get_schema(cls) -> typing.Optional[typing.Dict[str, typing.Any]]:
        return None

    async def configure(self, config: types.SimpleNamespace) -> None:
        pass

    def set_metadata(self, metadata: salobj.type_hints.BaseDdsDataType) -> None:
        """Set metadata fields in the provided struct, given the
        current configuration.

        Parameters
        ----------
        metadata : ``self.evt_metadata.DataType()``
            Metadata to update. Set those fields for which
            you have useful information.

        Notes
        -----
        This method is called after `configure` by `do_configure`.
        The script state will be `ScriptState.UNCONFIGURED`.
        """
        metadata.duration = self.timeout_start

    async def assert_liveliness(self) -> None:
        """Assert that the Scheduler is alive."""

        try:
            await self.scheduler_remote.evt_heartbeat.next(
                flush=True,
                timeout=salobj.base_script.HEARTBEAT_INTERVAL,
            )
        except asyncio.TimeoutError:
            raise AssertionError(
                f"No heartbeat from Scheduler in the last {salobj.base_script.HEARTBEAT_INTERVAL}s. "
                "Make sure it is running before trying to enable."
            )

    def get_summary_state(self) -> typing.Optional[salobj.State]:
        """Get Scheduler summary state."""
        current_summary_state = self.scheduler_remote.evt_summaryState.get()

        return (
            None
            if current_summary_state is None
            else salobj.State(current_summary_state.summaryState)
        )

    async def handle_no_summary_state_data(self) -> None:
        """Handle condition where no information about Scheduler summary state
        is available.

        Start by assuming Scheduler is in STANDBY, if this fails, assume it is
        in DISABLED and finally in ENABLED.
        """

        for coro in self._state_transition_methods_to_try:
            if await coro():
                return

        raise RuntimeError(f"Failed to transition CSC to {self.desired_state!r}.")

    async def _handle_csc_in_standby(self) -> bool:
        """Handle condition where CSC is in STANDBY."""

        try:
            await self.scheduler_remote.cmd_start.set_start(
                configurationOverride=self.configuration,
                timeout=self.timeout_start,
            )
        except salobj.AckError:
            self.log.warning("Sending start command failed. CSC not in STANDBY")
            return False
        else:
            await self.set_desired_state()
            return True

    async def _handle_csc_in_disabled_or_fault(self) -> bool:
        """Handle condition where CSC is either in DISABLED or FAULT."""
        try:
            await self.scheduler_remote.cmd_standby.set_start(
                timeout=self.timeout_start,
            )
        except salobj.AckError:
            self.log.warning(
                "Sending standby command failed. CSC not in DISABLED or FAULT."
            )
            return False
        else:
            await self.set_desired_state()
            return True

    async def _handle_csc_in_enabled(self) -> bool:
        """Handler condition where CSC is in ENABLED."""
        try:
            await self.scheduler_remote.cmd_disable.set_start(
                timeout=self.timeout_start,
            )
        except salobj.AckError:
            self.log.warning("Sending disabled command failed. CSC not in ENABLED.")
            return False
        else:
            await self.set_state_to_standby()
            await self.set_desired_state()
            return True

    async def set_state_to_standby(self) -> None:
        """Set Scheduler state to standby."""
        self.scheduler_remote.evt_summaryState.flush()
        await salobj.set_summary_state(
            self.scheduler_remote,
            salobj.State.STANDBY,
        )
        try:
            summary_state = await self.scheduler_remote.evt_summaryState.next(
                flush=False, timeout=self.timeout_start
            )
            summary_state = salobj.State(summary_state.summaryState)
            while summary_state != salobj.State.STANDBY:
                self.log.debug(
                    f"CSC in {summary_state.name}, waiting for it to be in STANDBY."
                )
                summary_state = await self.scheduler_remote.evt_summaryState.next(
                    flush=False, timeout=self.timeout_start
                )
                summary_state = salobj.State(summary_state.summaryState)

        except asyncio.TimeoutError:
            self.log.warning("Timeout waiting for summary state. Continuing.")

    async def set_desired_state(self) -> None:
        """Enable CSC."""
        await salobj.set_summary_state(
            self.scheduler_remote,
            self.desired_state,
            override=self.configuration,
        )

    async def run(self) -> None:
        """Enable the Scheduler and exit."""

        await self.checkpoint("Assert liveliness")
        await self.assert_liveliness()

        current_summary_state = self.get_summary_state()

        if current_summary_state is None:
            await self.checkpoint("Handling no summary state information")
            await self.handle_no_summary_state_data()
        elif (
            current_summary_state in {salobj.State.ENABLED, salobj.State.DISABLED}
            and self.desired_state != salobj.State.STANDBY
        ):
            await self.checkpoint(
                f"Reset summary state to STANDBY before setting to {self.desired_state!r}"
            )
            self.log.warning(
                f"Scheduler in {current_summary_state!r}, "
                f"sending CSC to STANDBY then to {self.desired_state!r}."
            )
            await self.set_state_to_standby()
            await self.checkpoint(f"Setting desired state: {self.desired_state!r}")
            await self.set_desired_state()
        else:
            await self.checkpoint(
                f"Setting desired state: {current_summary_state!r} -> {self.desired_state!r}"
            )
            await self.set_desired_state()

        await self.checkpoint(f"Scheduler {self.desired_state}")
