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

import yaml
from lsst.ts.salobj import type_hints
from lsst.ts.standardscripts import BaseBlockScript
from lsst.ts.standardscripts.utils import format_grid


class DummyBlockScript(BaseBlockScript):
    """This script replaces the maintel MoveP2P, which was used
     a test bed to extend BaseBlockScript.
       minimal stand-in for MoveP2P that extends BaseBlockScript.

    This script mimics the essential interface needed by the
    core tests, such as `move_p2p_radec` used in MoveP2P. Which
    now lives in ts_maintel_standardscripts
    """

    def __init__(self, index=None):
        super().__init__(index=index, descr="Dummy block script")
        self.mtcs = None  # Will be mocked in the tests
        self.grid = dict()
        self.pause_for = 0.0
        self.slew_time_average_guess = 15.0
        self.move_timeout = 120.0

    @classmethod
    def get_schema(cls):
        schema_yaml = """
        $schema: http://json-schema.org/draft-07/schema#
        $id: https://github.com/lsst-ts/ts_standardscripts/dummy_block_script.py
        title: DummyBlockScript v1
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

        await super().configure(config=config)

    def set_metadata(self, metadata: type_hints.BaseMsgType) -> None:
        """Set script metadata."""
        metadata.duration = self.slew_time_average_guess + self.pause_for * (
            len(self.grid.get("azel", dict(az=[]))["az"])
            + len(self.grid.get("radec", dict(ra=[]))["ra"])
        )

    async def run_block(self):
        """Implement the abstract method to mimic movement calls."""
        # For the dummy script, we'll mimic RA/Dec moves if defined
        if "radec" in self.grid:
            ra_list = self.grid["radec"]["ra"]
            dec_list = self.grid["radec"]["dec"]
            grid_size = len(ra_list)
            for i, (ra_val, dec_val) in enumerate(zip(ra_list, dec_list), start=1):
                await self.checkpoint(
                    f"{self.checkpoint_message}: radec grid {ra_val}/{dec_val} {i}/{grid_size}"
                )
                # We'll call the dummy movement method
                async with self.test_case_step():
                    await self.dummy_move_radec(
                        ra=ra_val, dec=dec_val, timeout=self.move_timeout
                    )
                await asyncio.sleep(self.pause_for)

    async def dummy_move_radec(self, *, ra, dec, timeout=None):
        """A dummy method to simulate a RA/Dec move for testing."""
        await self.mtcs.dummy_move_radec(ra=ra, dec=dec, timeout=timeout)
