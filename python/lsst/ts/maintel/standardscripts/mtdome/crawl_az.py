# This file is part of ts_maintel_standardscripts
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


__all__ = ["CrawlAz", "Direction"]

import asyncio
import enum

import yaml
from lsst.ts import salobj
from lsst.ts.xml.enums.MTDome import SubSystemId


class Direction(enum.IntEnum):
    ClockWise = enum.auto()
    CounterClockWise = enum.auto()


class CrawlAz(salobj.BaseScript):
    """Script that makes the MTDome crawl.

    This script is desined to be used by the day crew to move the dome
    around.

    Basically they pick a direction they want the dome to move and the
    dome will start moving in that direction. When they are happy with
    the position, just stops the script and it will take care of
    stopping the dome.
    """

    TIMEOUT_CMD = 60.0
    TIMEOUT_STD = 10.0

    def __init__(self, index):
        super().__init__(index=index, descr="MTDome CrawlAz.")

        self.mtdome = None
        self.direction = Direction.ClockWise

    @classmethod
    def get_schema(cls):
        schema_yaml = """
            $schema: http://json-schema.org/draft-07/schema#
            $id: https://github.com/lsst-ts/ts_standardscripts/maintel/mtdome/crawl_az.py
            title: CrawlAz v1
            description: Configuration for CrawlAz
            type: object
            properties:
                direction:
                    description: Which direction to move the dome?
                    type: string
                    default: ClockWise
                    enum: ["ClockWise", "CounterClockWise"]
            additionalProperties: false
        """
        return yaml.safe_load(schema_yaml)

    async def configure(self, config):
        self.direction = Direction[getattr(config, "direction", "ClockWise")]
        if self.mtdome is None:
            self.mtdome = salobj.Remote(
                self.domain,
                "MTDome",
                include=["summaryState"],
            )

            await self.mtdome.start_task

    def set_metadata(self, metadata) -> None:
        """Set script metadata.

        Parameters
        ----------
        metadata : `lsst.ts.salobj.base.ScriptMetadata`
            Script metadata.
        """
        pass

    async def run(self):

        self.log.info(f"Starting dome movement in the {self.direction!r} direction.")

        summary_state = await self.mtdome.evt_summaryState.aget(
            timeout=self.TIMEOUT_STD
        )

        current_state = salobj.State(summary_state.summaryState)

        if current_state != salobj.State.ENABLED:
            raise RuntimeError(
                "Dome must be in ENABLED, current state {current_state.name}."
            )

        self.mtdome.evt_summaryState.flush()

        await self.mtdome.cmd_crawlAz.set_start(
            velocity=0.5 * (1 if self.direction == Direction.ClockWise else -1),
            timeout=self.TIMEOUT_CMD,
        )

        while True:
            try:
                summary_state = await self.mtdome.evt_summaryState.next(
                    timeout=self.TIMEOUT_STD, flush=False
                )

                if summary_state.summaryState != salobj.State.ENABLED:
                    raise RuntimeError("Dome must be ENABLED.")
            except asyncio.TimeoutError:
                self.log.debug("Ignoring timeout error.")
            except asyncio.CancelledError:
                self.log.debug("Run method cancelled. Finishing.")
                return

    async def cleanup(self):

        self.log.info("Stopping dome.")

        try:
            await self.mtdome.cmd_crawlAz.set_start(
                velocity=0,
                timeout=self.TIMEOUT_CMD,
            )
        except Exception:
            self.log.exception("Error stopping dome crawl. Ignoring.")

        self.log.info("Waiting for dome to stop moving.")
        await asyncio.sleep(self.TIMEOUT_STD)

        try:
            await self.mtdome.cmd_stop.set_start(
                subSystemIds=SubSystemId.AMCS,
                timeout=self.TIMEOUT_CMD,
            )
        except Exception:
            self.log.exception("Error stopping the dome. Ignoring.")
