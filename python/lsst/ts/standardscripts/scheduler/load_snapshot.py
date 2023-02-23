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

__all__ = ["LoadSnapshot"]

import types
import typing

import yaml
from lsst.ts.idl.enums.Scheduler import SalIndex

from lsst.ts import salobj


class LoadSnapshot(salobj.BaseScript):
    """A base script that implements loading snapshots for the Scheduler.

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
            descr=f"Load snapshot for {scheduler_index.name} Scheduler",
        )

        self.scheduler_remote = salobj.Remote(
            domain=self.domain,
            name="Scheduler",
            index=scheduler_index,
            include=[
                "summaryState",
                "heartbeat",
                "largeFileObjectAvailable",
            ],
        )

        self.timeout_start = 30.0

        self.snapshot_uri: typing.Optional[str] = None

    @classmethod
    def get_schema(cls) -> typing.Optional[typing.Dict[str, typing.Any]]:
        return yaml.safe_load(
            """
$schema: http://json-schema.org/draft-07/schema#
$id: https://github.com/lsst-ts/ts_standardscripts/scheduler/base_load_snapshot.py
title: BaseLoadSnapshot v2
description: Configuration for loading scheduler snapshot.
type: object
properties:
    snapshot:
        description: >-
            Snapshot to load. This must be either a valid uri or the
            keyword "latest", which will cause it to load the last published
            snapshot.
        type: string
required:
    - snapshot
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

        self.log.info(f"Snapshot: {config.snapshot}.")

        if config.snapshot == "latest":
            self.log.debug("Loading latest snapshot.")
            latest_snapshot = (
                await self.scheduler_remote.evt_largeFileObjectAvailable.aget(
                    timeout=self.timeout_start
                )
            )
            if latest_snapshot is None:
                raise RuntimeError(
                    "No snapshot information from the Scheduler. "
                    "In order to load a snapshot with the 'latest' option, the "
                    "Scheduler must have published at least one snapshot."
                )
            else:
                self.log.info(f"Latest snapshot uri: {latest_snapshot.url}")
            self.snapshot_uri = latest_snapshot.url
        else:
            self.snapshot_uri = config.snapshot

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
        await self.checkpoint("Loading snapshot")
        await self.scheduler_remote.cmd_load.set_start(
            uri=self.snapshot_uri, timeout=self.timeout_start
        )
        await self.checkpoint("Snapshot loaded")
