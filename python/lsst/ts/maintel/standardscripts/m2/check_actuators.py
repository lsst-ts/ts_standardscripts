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

__all__ = ["CheckActuators"]


import asyncio
import time

import numpy as np
import yaml
from lsst.ts.idl.enums.Script import ScriptState
from lsst.ts.observatory.control.maintel.mtcs import MTCS
from lsst.ts.salobj import AckError, AckTimeoutError
from lsst.ts.standardscripts.base_block_script import BaseBlockScript

# TODO: DM-41592 move constants from lsst.ts.m2com to ts-xml
NUM_ACTUATOR = 78
NUM_TANGENT_LINK = 6


class CheckActuators(BaseBlockScript):
    """Perform a M2 bump test on either a selection of individual
    actuators or on all axial actuators.

    Parameters
    ----------
    index : `int`
        Index of Script SAL component.

    Notes
    -----

    **Checkpoints**

    - "Running bump test on FA ID: {id}.": Check individual actuator.
    - "M2 bump test completed.": Check complete.

    """

    def __init__(self, index):
        super().__init__(index=index, descr="Bump Test on M2 Axial Actuators")

        self.mtcs = None

        # Average duration (seconds) of a bump test on a single actuator
        self.time_one_bump = 120

        # default period of bump test in seconds
        self.period = 60

        # default +/- force to apply during bump test in N
        self.force = 10

    async def assert_feasibility(self):
        """Verify that the system is in a feasible state before
        running bump test.
        """

        for comp in self.mtcs.components_attr:
            if comp != "mtm2":
                self.log.debug(f"Ignoring component {comp}.")
                setattr(self.mtcs.check, comp, False)

        # Check all enabled and liveliness
        await asyncio.gather(
            self.mtcs.assert_all_enabled(),
            self.mtcs.assert_liveliness(),
        )

    @classmethod
    def get_schema(cls):
        url = "https://github.com/lsst-ts/"
        path = (
            "ts_externalscripts/blob/main/python/lsst/ts/standardscripts/"
            "maintel/m2/check_actuators.py"
        )
        schema_yaml = f"""
        $schema: http://json-schema.org/draft-07/schema#
        $id: {url}{path}
        title: CheckAcutators v1
        description: Configuration for Maintel M2 bump test SAL Script.
        type: object
        properties:
            period:
                description: Period, in seconds, for each step of bump test, two steps total.
                type: number
                default: 60
            force:
                description: Force, in N, the +/- force to apply during bump test.
                type: number
                default: 10
            actuators:
                description: Actuators to run the bump test.
                oneOf:
                  - type: array
                    items:
                      type: number
                      minimum: 0
                      maximum: {NUM_ACTUATOR - NUM_TANGENT_LINK}
                    minItems: 1
                    uniqueItems: true
                    additionalItems: false
                  - type: string
                    enum: ["all"]
                default: "all"
            ignore_actuators:
                description: Actuators to ignore during the bump test.
                type: array
                items:
                    type: number
                    minimum: 0
                    maximum: {NUM_ACTUATOR - NUM_TANGENT_LINK}
                default: []
        additionalProperties: false
        """
        schema_dict = yaml.safe_load(schema_yaml)

        base_schema_dict = super().get_schema()

        for properties in base_schema_dict["properties"]:
            schema_dict["properties"][properties] = base_schema_dict["properties"][
                properties
            ]

        return schema_dict

    async def configure(self, config):
        """Configure the script.

        Parameters
        ----------
        config : `types.SimpleNamespace`
            Configuration
        """

        if self.mtcs is None:
            self.mtcs = MTCS(
                domain=self.domain,
                log=self.log,
            )
            await self.mtcs.start_task

        # Get list of M2 hardpoints from mtcs
        self.hardpoint_ids = await self.mtcs.get_m2_hardpoints()

        # Getting list of actuator ids
        num_axial_actuator = NUM_ACTUATOR - NUM_TANGENT_LINK
        self.axial_actuator_ids = list(
            [
                actuator
                for actuator in np.arange(num_axial_actuator)
                if actuator + 1 not in self.hardpoint_ids
            ]
        )

        # Actuators that will be effectively tested, filtering out hardpoints
        # (which are 1 indexed, csc is 0 indexed)
        if config.actuators == "all":
            self.actuators_to_test = self.axial_actuator_ids
        else:
            # check that no actuators are hardpoints
            for actuator in config.actuators:
                if actuator + 1 in self.hardpoint_ids:
                    raise ValueError(
                        f"Cannot run bump test on actuator {actuator},"
                        "it is currently configured as a hardpoint"
                    )
                elif actuator + 1 not in self.axial_actuator_ids:
                    raise ValueError(
                        f"Cannot run bump test on actuator {actuator}, it is not a valid axial actuator."
                    )

            self.actuators_to_test = config.actuators

        if config.ignore_actuators:
            self.actuators_to_test = [
                actuator
                for actuator in self.actuators_to_test
                if actuator not in config.ignore_actuators
            ]
        if hasattr(config, "period"):
            self.period = config.period
        if hasattr(config, "force"):
            self.force = config.force

        await super().configure(config=config)

    def set_metadata(self, metadata):
        """Set metadata."""

        metadata.duration = self.time_one_bump * (len(self.actuators_to_test))

    async def run_block(self):
        await self.assert_feasibility()
        start_time = time.monotonic()

        self.failed_actuator_ids = []
        for actuator in self.actuators_to_test:
            await self.mtcs.assert_all_enabled()

            # Checkpoint
            await self.checkpoint(f"Running bump test on M2 Axial FA ID: {actuator} ")

            try:
                await self.mtcs.run_m2_actuator_bump_test(
                    actuator=actuator,
                    period=self.period,
                    force=self.force,
                )
            except (AckError, AckTimeoutError):
                self.failed_actuator_ids.append(actuator)
                self.log.exception(
                    f"Failed to run bump test on AXIAL FA ID {actuator}."
                )

        end_time = time.monotonic()
        elapsed_time = end_time - start_time

        # Final checkpoint
        await self.checkpoint(
            f"M2 bump test completed. It took {elapsed_time:.2f} seconds."
        )

        # Final message with bump test results/status
        if not self.failed_actuator_ids:
            self.log.info("All actuators PASSED the bump test.")
        else:
            error_message = (
                f"Actuators {self.failed_actuator_ids} FAILED the bump test."
            )
            self.log.error(error_message)
            raise RuntimeError(error_message)

    async def cleanup(self):
        if self.state.state != ScriptState.ENDING:
            try:
                self.log.warning("M2 bump test stopped. Killing actuator forces.")

                await self.mtcs.stop_m2_bump_test()

            except Exception:
                self.log.exception("Unexpected exception in stop_m2_bump_test.")
