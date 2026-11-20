# This file is part of ts_standardscripts.
#
# Developed for the Vera C. Rubin Observatory Telescope and Site Systems.
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
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <https://www.gnu.org/licenses/>.

__all__ = ["AddBlock"]

import asyncio
import math
import types

import yaml
from lsst.ts import salobj
from lsst.ts.xml.enums.Scheduler import SalIndex
from lsst.ts.xml.enums.Watcher import AlarmSeverity
from lsst.ts.xml.sal_enums import State


class AddBlock(salobj.BaseScript):
    """A base script that implements loading BLOCKS to the Scheduler.

    Parameters
    ----------
    index : `int`
        Index of Script SAL component.
    scheduler_index : `int`
        Index of the Scheduler to enable.
    mute_alarms : `list`[`tuple`[`str`, `AlarmSeverity`]], optional.
        List of Watcher alarm names to mute.
    """

    def __init__(
        self,
        index: int,
        scheduler_index: SalIndex,
        mute_alarms: list[tuple[str, AlarmSeverity]] | None = None,
    ) -> None:
        super().__init__(
            index=index,
            descr=f"Load block to the {scheduler_index.name} Scheduler",
        )

        self.scheduler_remote = salobj.Remote(
            domain=self.domain,
            name="Scheduler",
            index=scheduler_index,
        )

        self.mute_alarms = mute_alarms
        self.short_timeout = 5.0

    @classmethod
    def get_schema(cls):
        schema_yaml = """
            $schema: http://json-schema.org/draft-07/schema#
            $id: https://github.com/lsst-ts/ts_standardscripts/scheduler/base_load_snapshot.py
            title: BaseAddBlock v1
            description: Configuration for adding BLOCK to scheduler.
            type: object
            properties:
                id:
                    type: string
                    description: id of BLOCK to load. This must be a valid BLOCK-ID.
                override:
                    type: object
                    description: >-
                        Configuration overrides to pass to the BLOCK to be loaded. Must be
                        provided in YAML format. This feature is not yet implemented in the
                        Scheduler CSC.
                    additionalProperties: true
            required: [id]
            additionalProperties: false
            """
        return yaml.safe_load(schema_yaml)

    async def configure(self, config: types.SimpleNamespace) -> None:
        """Configure the script.

        Parameters
        ----------
        config : `types.SimpleNamespace`
            Configuration.
        """

        self.id = config.id
        self.override = getattr(config, "override", None)
        self.timeout_start = 30.0

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

    async def run(self) -> None:
        # Prevent script from running on different queues
        script_queue_index = math.floor(self.salinfo.index / 100000)
        if script_queue_index != self.scheduler_remote.salinfo.index.value:
            raise RuntimeError(
                f"Script with index {self.salinfo.index} cannot run in"
                f" {self.scheduler_remote.salinfo.index.name} queue."
            )

        if self.mute_alarms is not None and self.mute_alarms:
            mute_alarms_str = ", ".join(
                [f"({name}: {level!r})" for name, level in self.mute_alarms]
            )
            await self.checkpoint(f"Muting watcher alarms: {mute_alarms_str}.")
            await self._handle_watcher_alarms()
        await self.checkpoint(f"Loading {self.id} into scheduler")
        await self.scheduler_remote.cmd_addBlock.set_start(
            id=self.id,
            override=yaml.safe_dump(self.override),
            timeout=self.timeout_start,
        )
        await self.checkpoint("BLOCK successfully loaded")

    async def _handle_watcher_alarms(self):
        """Handle muting watcher alarms."""

        if self.mute_alarms is None or not self.mute_alarms:
            self.log.info("No alarms to mute.")
            return

        async with salobj.Remote(
            self.domain, "Watcher", include=["summaryState", "heartbeat"]
        ) as watcher_remote:
            try:
                await watcher_remote.evt_heartbeat.next(
                    flush=True, timeout=self.short_timeout
                )
            except asyncio.TimeoutError:
                self.log.info(
                    f"No heartbeat from watcher in the past {self.short_timeout}s; "
                    "will not mute alarms."
                )
                return

            try:
                watcher_summary_state = await watcher_remote.evt_summaryState.aget(
                    timeout=self.timeout_start
                )
            except asyncio.TimeoutError:
                self.log.info(
                    "Cannot determine watcher summary state; will not mute alarms."
                )
                return
            else:
                if watcher_summary_state.summaryState != State.ENABLED:
                    self.log.info(
                        f"Watcher summary state {State(watcher_summary_state.summaryState)!r}, "
                        "not enabled. Nothing to do."
                    )
                    return

            for name, severity in self.mute_alarms:
                try:
                    await watcher_remote.cmd_mute.set_start(
                        name=name,
                        duration=30.0,
                        severity=severity,
                        mutedBy="AddBlock Script",
                        timeout=self.timeout_start,
                    )
                except asyncio.TimeoutError:
                    self.log.info("Timeout muting alarm; ignoring.")
                except salobj.AckError:
                    self.log.info("Command failed; ignoring.", exc_info=True)
