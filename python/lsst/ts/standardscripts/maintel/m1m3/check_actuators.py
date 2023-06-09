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

__all__ = ["CheckActuators"]


import asyncio
import time

import yaml
from lsst.ts.cRIOpy.M1M3FATable import FATABLE, FATABLE_ID
from lsst.ts.idl.enums.MTM1M3 import BumpTest, DetailedState
from lsst.ts.idl.enums.Script import ScriptState
from lsst.ts.observatory.control.maintel.mtcs import MTCS, MTCSUsages

from ...base_block_script import BaseBlockScript


class CheckActuators(BaseBlockScript):
    """Perform a M1M3 bump test on either a selection of individual
    actuators or on all actuators.

    Parameters
    ----------
    index : `int`
        Index of Script SAL component.

    Notes
    -----

    In case of dual actuators both cylinders will be tested consecutively.
    The Script will fail if M1M3 mirror is raised.

    **Checkpoints**

    - "Running bump test on FA ID: {id}.": Check individual actuator.
    - "M1M3 bump test completed.": Check complete.

    """

    def __init__(self, index, add_remotes: bool = True):
        super().__init__(index=index, descr="Bump Test on M1M3 Actuators")

        self.mtcs = MTCS(
            domain=self.domain,
            intended_usage=None if add_remotes else MTCSUsages.DryTest,
            log=self.log,
        )

        # Average duration (seconds) of a bump test on a single actuator
        self.time_one_bump = 25

        # Getting list of actuator ids from mtcs
        self.m1m3_actuator_ids = self.mtcs.get_m1m3_actuator_ids()
        self.m1m3_secondary_actuator_ids = self.mtcs.get_m1m3_actuator_secondary_ids()

        # Actuators that will be effectively tested
        self.actuators_to_test = self.m1m3_actuator_ids.copy()

    async def assert_feasibility(self):
        """Verify that the system is in a feasible state before
        running bump test. Note that M1M3 mirror should be in lowered
        position.
        """

        for comp in self.mtcs.components_attr:
            if comp != "mtm1m3":
                self.log.debug(f"Ignoring component {comp}.")
                setattr(self.mtcs.check, comp, False)

        # Check all enabled and liveliness
        await asyncio.gather(
            self.mtcs.assert_all_enabled(),
            self.mtcs.assert_liveliness(),
        )
        # Check if m1m3 detailed state is either PARKED or PARKEDENGINEERING
        expected_states = {DetailedState.PARKED, DetailedState.PARKEDENGINEERING}
        try:
            await self.mtcs.assert_m1m3_detailed_state(expected_states)
        except AssertionError:
            raise RuntimeError(
                "Please park M1M3 before proceeding with the bump test. This can be done "
                "by lowering the mirror or enabling the M1M3 CSC."
            )

    @classmethod
    def get_schema(cls):
        m1m3_actuator_ids_str = ",".join([str(fa[FATABLE_ID]) for fa in FATABLE])

        url = "https://github.com/lsst-ts/"
        path = (
            "ts_externalscripts/blob/main/python/lsst/ts/standardscripts/"
            "maintel/m1m3/check_actuators.py"
        )
        schema_yaml = f"""
        $schema: http://json-schema.org/draft-07/schema#
        $id: {url}{path}
        title: CheckAcutators v1
        description: Configuration for Maintel bump test SAL Script.
        type: object
        properties:
            actuators:
                description: Actuators to run the bump test.
                oneOf:
                  - type: array
                    items:
                      type: number
                      enum: [{m1m3_actuator_ids_str}]
                    minItems: 1
                    uniqueItems: true
                    additionalItems: false
                  - type: string
                    enum: ["all"]
                default: "all"
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

        # Getting actuators to be tested.
        self.actuators_to_test = (
            self.m1m3_actuator_ids if config.actuators == "all" else config.actuators
        )
        await super().configure(config=config)

    def set_metadata(self, metadata):
        """Set metadata."""

        # Getting total number of secondary actuators to be tested
        total_tested_secondary = sum(
            [
                1
                for actuator in self.actuators_to_test
                if self.has_secondary_actuator(actuator)
            ]
        )

        # Setting metadata
        metadata.duration = self.time_one_bump * (
            len(self.actuators_to_test) + total_tested_secondary
        )

    def has_secondary_actuator(self, actuator_id: int) -> bool:
        """Determines whether a given actuator has a
        secondary axis or not.
        """

        return actuator_id in self.m1m3_secondary_actuator_ids

    async def run_block(self):
        await self.assert_feasibility()
        start_time = time.monotonic()

        # Get M1M3 detailed state
        detailed_state = DetailedState(
            (
                await self.mtcs.rem.mtm1m3.evt_detailedState.aget(
                    timeout=self.mtcs.fast_timeout,
                )
            ).detailedState
        )
        self.log.info(f"Current M1M3 detailed state: {detailed_state!r}.")

        # Put M1M3 in engineering mode
        await self.mtcs.enter_m1m3_engineering_mode()

        failed_actuators_id = []
        failed_primary, failed_secondary = [], []
        for i, actuator_id in enumerate(self.actuators_to_test):
            await self.mtcs.assert_all_enabled()

            # Determine if actuator has a secondary actuator
            secondary_exist = self.has_secondary_actuator(actuator_id)

            # Checkpoint
            primary_index = self.m1m3_actuator_ids.index(actuator_id)
            if secondary_exist:
                secondary_index = self.m1m3_secondary_actuator_ids.index(actuator_id)
                await self.checkpoint(
                    f"Running bump test on DAA FA ID: {actuator_id} "
                    f"(Primary/Secondary: {primary_index}/{secondary_index})"
                )
            else:
                await self.checkpoint(
                    f"Running bump test on SAA FA ID: {actuator_id} "
                    f"(Primary {primary_index})"
                )

            try:
                await self.mtcs.run_m1m3_actuator_bump_test(
                    actuator_id=actuator_id,
                    primary=True,
                    secondary=secondary_exist,
                )
            # raise a RuntimeError if the bump test fails
            except RuntimeError:
                failed_actuators_id.append(actuator_id)
                self.log.exception(f"Failed to run bump test on FA ID {actuator_id}.")

            # Getting test status
            (
                primary_status,
                secondary_status,
            ) = await self.mtcs.get_m1m3_bump_test_status(actuator_id=actuator_id)

            secondary_status_text = (
                f"Secondary FA (Index {secondary_index}): "
                f"{secondary_status.name.upper()}."
                if secondary_exist
                else ""
            )
            self.log.info(
                f"Bump test done for {i + 1} of {len(self.actuators_to_test)}. "
                f"FA ID {actuator_id}. Primary FA (Index {primary_index}): "
                f"{primary_status.name.upper()}. "
                f"{secondary_status_text}"
            )

            # Getting primary indexes for failures
            if primary_status == BumpTest.FAILED:
                failed_primary.append((actuator_id, primary_index))

            if secondary_exist:
                if secondary_status == BumpTest.FAILED:
                    failed_secondary.append((actuator_id, secondary_index))

        end_time = time.monotonic()
        elapsed_time = end_time - start_time

        # Final checkpoint
        await self.checkpoint(
            f"M1M3 bump test completed. It took {elapsed_time:.2f} seconds."
        )

        # Final message with bump test results/status
        if not failed_actuators_id:
            self.log.info("All actuators PASSED the bump test.")
        else:
            failed_primary_str = ", ".join(
                f"{failed[0]}:{failed[1]}" for failed in failed_primary
            )
            failed_secondary_str = ", ".join(
                f"{failed[0]}:{failed[1]}" for failed in failed_secondary
            )
            error_message = (
                f"Actuators {failed_actuators_id} FAILED the bump test. \n "
                f"SAA (ID, Pri Index): {failed_primary_str} \n "
                f"DAA (ID, Sec Index): {failed_secondary_str}"
            )
            self.log.error(error_message)
            raise RuntimeError(error_message)

    async def cleanup(self):
        if self.state.state != ScriptState.ENDING:
            try:
                self.log.warning("M1M3 bump test stopped. Killing actuator forces.")

                await self.mtcs.stop_m1m3_bump_test()

            except Exception:
                self.log.exception("Unexpected exception in stop_m1m3_bump_test.")

        # Exiting engineering mode
        await self.mtcs.exit_m1m3_engineering_mode()
