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

import asyncio

import yaml
from lsst.ts.idl.enums.Script import ScriptState
from lsst.ts.observatory.control.maintel import MTCS
from lsst.ts.salobj import type_hints
from lsst.ts.standardscripts.base_block_script import BaseBlockScript
from lsst.ts.standardscripts.utils import format_grid


class MoveP2P(BaseBlockScript):
    """Move Telescope using point to point trajectory instead of traditional
    slew/tracking.
    """

    def __init__(self, index: int) -> None:
        super().__init__(index, descr="Move Telescope using point to point trajectory.")

        self.mtcs = None
        self.grid = dict()
        self.pause_for = 0.0
        # A guess to average slew time.
        self.slew_time_average_guess = 15.0
        self.move_timeout = 120.0

    async def configure_tcs(self) -> None:
        """Handle creating MTCS object and waiting for remote to start."""
        if self.mtcs is None:
            self.log.debug("Creating MTCS.")
            self.mtcs = MTCS(
                domain=self.domain,
                log=self.log,
            )
            await self.mtcs.start_task
        else:
            self.log.debug("MTCS already defined, skipping.")

    @classmethod
    def get_schema(cls):
        schema_yaml = """
        $schema: http://json-schema.org/draft-07/schema#
        $id: https://github.com/lsst-ts/ts_standardscripts/maintel/move_p2p.py
        title: MoveP2P v1
        description: Configuration for BaseTrackTarget.
        type: object
        additionalProperties: false
        properties:
            az:
                description: Azimuth (deg). Must be used alongside el.
                oneOf:
                    - type: number
                    - type: array
                      values:
                        type: number
            el:
                description: Elevation (deg). Must be used alongside az.
                oneOf:
                    - type: number
                    - type: array
                      values:
                        type: number
            ra:
                description: Right ascension (hour). Must be used alongside dec.
                oneOf:
                    - type: number
                    - type: array
                      values:
                        type: number
            dec:
                description: Declination (deg). Must be used alongside ra.
                oneOf:
                    - type: number
                    - type: array
                      values:
                        type: number
            pause_for:
                description: >-
                    If slewing to more than one target, how long to pause
                    between positions (in seconds).
                type: number
                default: 0.0
            ignore:
                description: >-
                    CSCs from the group to ignore in status check. Name must
                    match those in self.group.components, e.g.; hexapod_1.
                type: array
                items:
                    type: string
            move_timeout:
                description: Timeout for move command.
                type: number
                default: 120.0
        oneOf:
            - required:
                - az
                - el
            - required:
                - ra
                - dec
        """
        schema_dict = yaml.safe_load(schema_yaml)

        base_schema_dict = super().get_schema()

        for properties in base_schema_dict["properties"]:
            schema_dict["properties"][properties] = base_schema_dict["properties"][
                properties
            ]

        return schema_dict

    async def configure(self, config):
        """Configure script."""

        if hasattr(config, "az") and hasattr(config, "el"):
            az, el = format_grid(config.az, config.el)
            self.grid["azel"] = dict(az=az, el=el)

        if hasattr(config, "ra") and hasattr(config, "dec"):
            ra, dec = format_grid(config.ra, config.dec)
            self.grid["radec"] = dict(ra=ra, dec=dec)

        self.pause_for = config.pause_for
        self.move_timeout = config.move_timeout

        await self.configure_tcs()

        for comp in getattr(config, "ignore", []):
            if comp not in self.mtcs.components_attr:
                self.log.warning(
                    f"Component {comp} not in CSC Group. "
                    f"Must be one of {self.mtcs.components_attr}. Ignoring."
                )
            else:
                self.log.debug(f"Ignoring component {comp}.")
                setattr(self.mtcs.check, comp, False)

        await super().configure(config=config)

    def set_metadata(self, metadata: type_hints.BaseMsgType) -> None:
        """Set script metadata."""
        metadata.duration = self.slew_time_average_guess + self.pause_for * (
            len(self.grid.get("azel", dict(az=[]))["az"])
            + len(self.grid.get("radec", dict(ra=[]))["ra"])
        )

    async def run_block(self):
        """Execute script operations."""

        if "azel" in self.grid:
            grid_size = len(self.grid["azel"]["az"])
            for i, az, el in zip(
                range(grid_size), self.grid["azel"]["az"], self.grid["azel"]["el"]
            ):
                await self.checkpoint(
                    f"{self.checkpoint_message}: azel grid {az}/{el} {i+1}/{grid_size}"
                )
                self.log.info(f"Moving telescope to {az=},{el=}.")
                async with self.test_case_step():
                    await self.mtcs.move_p2p_azel(
                        az=az,
                        el=el,
                        timeout=self.move_timeout,
                    )
                self.log.info(f"Pausing for {self.pause_for}s.")
                await asyncio.sleep(self.pause_for)

        if "radec" in self.grid:
            grid_size = len(self.grid["radec"]["ra"])
            for i, ra, dec in zip(
                range(grid_size), self.grid["radec"]["ra"], self.grid["radec"]["dec"]
            ):
                await self.checkpoint(
                    f"{self.checkpoint_message}: radec grid {ra}/{dec} {i+1}/{grid_size}"
                )
                self.log.info(f"Moving telescope to {ra=},{dec=}.")
                async with self.test_case_step():
                    await self.mtcs.move_p2p_radec(
                        ra=ra,
                        dec=dec,
                        timeout=self.move_timeout,
                    )
                self.log.info(f"Pausing for {self.pause_for}s.")
                await asyncio.sleep(self.pause_for)

    async def cleanup(self):
        if self.state.state != ScriptState.ENDING:
            # abnormal termination
            self.log.warning(
                f"Terminating with state={self.state.state}: stop telescope."
            )
            try:
                await self.mtcs.rem.mtmount.cmd_stop.start(
                    timeout=self.mtcs.long_timeout
                )
            except asyncio.TimeoutError:
                self.log.exception("Stop command timed out during cleanup procedure.")
            except Exception:
                self.log.exception("Unexpected exception while stopping telescope.")
