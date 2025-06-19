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

__all__ = ["Stop"]

import math
import types
import typing

import yaml
from lsst.ts import salobj
from lsst.ts.xml.enums.Scheduler import SalIndex


class Stop(salobj.BaseScript):
    """A base script that implements resuming the Scheduler.

    Parameters
    ----------
    index : `int`
        Index of Script SAL component.
    scheduler_index : `int`
        Index of the Scheduler to enable.
    """

    def __init__(self, index: int, scheduler_index: SalIndex) -> None:
        super().__init__(
            index=index,
            descr=f"Stop {scheduler_index.name} Scheduler",
        )

        self.scheduler_remote = salobj.Remote(
            domain=self.domain,
            name="Scheduler",
            index=scheduler_index,
            include=[],
        )

        self.timeout_start = 30.0
        self.stop = False

    @classmethod
    def get_schema(cls) -> typing.Optional[typing.Dict[str, typing.Any]]:
        return yaml.safe_load(
            """
$schema: http://json-schema.org/draft-07/schema#
$id: https://github.com/lsst-ts/ts_standardscripts/scheduler/base_stop.py
title: BaseStop v2
description: Configuration for stopping scheduler.
type: object
properties:
    stop:
        description: >-
            Should the Scheduler stop current observations in the queue?
        type: boolean
        default: false
additionalProperties: false
        """
        )

    async def configure(self, config: types.SimpleNamespace) -> None:
        """Configure the script.

        Parameters
        ----------
        config : `types.SimpleNamespace`
            Configuration.
        """
        self.stop = config.stop

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

        await self.checkpoint("Stopping scheduler")
        await self.scheduler_remote.cmd_stop.set_start(
            abort=self.stop, timeout=self.timeout_start
        )
        await self.checkpoint("Scheduler stopped")
