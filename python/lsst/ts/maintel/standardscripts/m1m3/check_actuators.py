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
import warnings

import yaml

try:
    from lsst.ts.xml.tables.m1m3 import FATable
except ImportError:
    from lsst.ts.criopy.M1M3FATable import FATABLE as FATable

from lsst.ts.idl.enums.MTM1M3 import BumpTest
from lsst.ts.idl.enums.Script import ScriptState
from lsst.ts.observatory.control.maintel.mtcs import MTCS
from lsst.ts.standardscripts.base_block_script import BaseBlockScript
from lsst.ts.utils import make_done_future
from lsst.ts.xml.tables.m1m3 import force_actuator_from_id

try:
    from lsst.ts.idl.enums.MTM1M3 import DetailedState
except ImportError:
    warnings.warn(
        "Could not import MTM1M3 from lsst.ts.idl; importing from lsst.ts.xml",
        UserWarning,
    )
    from lsst.ts.xml.enums.MTM1M3 import DetailedStates as DetailedState


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

    def __init__(self, index):
        super().__init__(index=index, descr="Bump Test on M1M3 Actuators")

        self.mtcs = None

        # Average duration (seconds) of a bump test on a single actuator
        self.time_one_bump = 25

        # Getting list of actuator ids from mtcs
        self.m1m3_actuator_ids = None
        self.m1m3_secondary_actuator_ids = None

        # Actuators that will be effectively tested
        self.actuators_to_test = None

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
        m1m3_actuator_ids_str = ",".join([str(fa.actuator_id) for fa in FATable])

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
                    enum: ["all", "last_failed"]
                default: "all"
            ignore_actuators:
                description: Actuators to ignore during the bump test.
                type: array
                items:
                    type: number
                    enum: [{m1m3_actuator_ids_str}]
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

        self.config = config

        await self.configure_tcs()

        # Get actuators to be tested.
        # (if "last_failed" is used, select all actuators for later filtering)
        self.actuators_to_test = (
            self.m1m3_actuator_ids
            if config.actuators in ["all", "last_failed"]
            else config.actuators
        )
        if config.ignore_actuators:
            self.actuators_to_test = [
                actuator_id
                for actuator_id in self.actuators_to_test
                if actuator_id not in config.ignore_actuators
            ]

        await super().configure(config=config)

    async def configure_tcs(self):
        if self.mtcs is None:
            self.mtcs = MTCS(self.domain, log=self.log)
            await self.mtcs.start_task

        # Getting list of actuator ids from mtcs
        self.m1m3_actuator_ids = self.mtcs.get_m1m3_actuator_ids()
        self.m1m3_secondary_actuator_ids = self.mtcs.get_m1m3_actuator_secondary_ids()

        self.actuators_to_test = self.m1m3_actuator_ids.copy()

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

    async def actuator_last_test_failed(self, actuator_id: int) -> bool:
        """Determines whether the last bump test for a given actuator
        failed."""
        primary, secondary = await self.mtcs.get_m1m3_bump_test_status(actuator_id)
        return primary == BumpTest.FAILED or secondary == BumpTest.FAILED

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

        # Filter actuator_to_test when the last_failed option is used
        if self.config.actuators == "last_failed":
            actuators_mask = await asyncio.gather(
                *[
                    self.actuator_last_test_failed(actuator_id)
                    for actuator_id in self.actuators_to_test
                ]
            )
            self.actuators_to_test = [
                actuator_id
                for actuator_id, mask in zip(self.actuators_to_test, actuators_mask)
                if mask
            ]
            self.log.info(
                f"Selecting actuators that failed the last bump test: {self.actuators_to_test!r}."
            )

        # Put M1M3 in engineering mode
        await self.mtcs.enter_m1m3_engineering_mode()

        # List to capture failures with full details
        list_of_failures = []

        timer_task = make_done_future()

        for i, actuator_id in enumerate(self.actuators_to_test):
            await self.mtcs.assert_all_enabled()

            # Get the actuator type (SAA or DAA)
            actuator_type = force_actuator_from_id(actuator_id).actuator_type.name
            secondary_exist = self.has_secondary_actuator(actuator_id)

            # Get primary and secondary indexes
            primary_index = self.m1m3_actuator_ids.index(actuator_id)
            secondary_index = None
            if secondary_exist:
                secondary_index = self.m1m3_secondary_actuator_ids.index(actuator_id)

            # Checkpoint before running the bump test
            if secondary_exist:
                await self.checkpoint(
                    f"Running bump test on DAA FA ID: {actuator_id} "
                    f"(Primary/Secondary: {primary_index}/{secondary_index})"
                )
            else:
                await self.checkpoint(
                    f"Running bump test on SAA FA ID: {actuator_id} "
                    f"(Primary {primary_index})"
                )

            # Run the bump test
            try:
                if not timer_task.done():
                    self.log.debug("Waiting timer task before running bump test.")
                    await timer_task
                    self.log.debug("Timer task done. Running bump test.")

                await self.mtcs.run_m1m3_actuator_bump_test(
                    actuator_id=actuator_id,
                    primary=True,
                    secondary=secondary_exist,
                )
            except RuntimeError:
                list_of_failures.append(
                    (actuator_id, actuator_type, primary_index, None)
                )
                self.log.exception(
                    f"Failed to run bump test on FA ID {actuator_id}. Creating timer task for next test."
                )
                timer_task = asyncio.create_task(asyncio.sleep(self.time_one_bump))

            # Getting test status
            primary_status, secondary_status = (
                await self.mtcs.get_m1m3_bump_test_status(actuator_id=actuator_id)
            )

            # Log status update after bump test
            secondary_status_text = (
                f"Secondary FA (Index {secondary_index}): {secondary_status.name.upper()}."
                if secondary_exist
                else ""
            )
            self.log.info(
                f"Bump test done for {i + 1} of {len(self.actuators_to_test)}. "
                f"FA ID {actuator_id} ({actuator_type}). Primary FA (Index {primary_index}): "
                f"{primary_status.name.upper()}. {secondary_status_text}"
            )

            # Check primary failure
            if primary_status == BumpTest.FAILED:
                self.log.debug(
                    f"Primary failed for Actuator ID {actuator_id}, Pri Index {primary_index}"
                )
                primary_index_of_failure = primary_index
            else:
                primary_index_of_failure = None

            # Check secondary failure
            if secondary_exist and secondary_status == BumpTest.FAILED:
                self.log.debug(
                    f"Secondary failed for Actuator ID {actuator_id}, Sec Index {secondary_index}"
                )
                secondary_index_of_failure = secondary_index
            else:
                secondary_index_of_failure = None

            # Find if actuator is already in list_of_failures
            actuator_failure = next(
                (item for item in list_of_failures if item[0] == actuator_id), None
            )

            # Append or update failures in list_of_failures
            if (
                primary_index_of_failure is not None
                or secondary_index_of_failure is not None
            ):
                if actuator_failure:
                    # Update primary or secondary failure only if they failed
                    updated_primary_index = (
                        primary_index_of_failure
                        if primary_index_of_failure is None
                        else actuator_failure[2]  # Keep the original (None or failure)
                    )
                    updated_secondary_index = (
                        secondary_index_of_failure
                        if secondary_index_of_failure is not None
                        else actuator_failure[3]  # Keep the original (None or failure)
                    )

                    # Only update the entry if the failure has changed
                    list_of_failures[list_of_failures.index(actuator_failure)] = (
                        actuator_id,
                        actuator_type,
                        updated_primary_index,
                        updated_secondary_index,
                    )
                    self.log.debug(
                        f"Updated in list_of_failures: Actuator ID {actuator_id}, Type {actuator_type}, "
                        f"Primary Index {updated_primary_index}, Secondary Index {updated_secondary_index}"
                    )
                else:
                    # Add new entry only with failure information
                    # (ignores passed tests)
                    list_of_failures.append(
                        (
                            actuator_id,
                            actuator_type,
                            primary_index_of_failure,
                            secondary_index_of_failure,
                        )
                    )
                    self.log.debug(
                        f"Appending to list_of_failures: Actuator ID {actuator_id}, Type {actuator_type}, "
                        f"Primary Index {primary_index_of_failure}, Secondary Index "
                        f"{secondary_index_of_failure}."
                    )

        end_time = time.monotonic()
        elapsed_time = end_time - start_time

        # Final checkpoint
        await self.checkpoint(
            f"M1M3 bump test completed. It took {elapsed_time:.2f} seconds."
        )

        # Generating final report from list_of_failures
        if not list_of_failures:
            self.log.info("All actuators PASSED the bump test.")
        else:
            # Collect the failed actuator IDs for the header
            failed_actuators_id = [fail[0] for fail in list_of_failures]

            # Create formatted output for SAA and DAA failures
            failed_saa_str = "\n".join(
                f"  - Actuator ID {actuator_id}: Pri Index {primary_index}"
                for actuator_id, actuator_type, primary_index, _ in list_of_failures
                if actuator_type == "SAA" and primary_index is not None
            )

            failed_daa_str = "\n".join(
                f"  - Actuator ID {actuator_id}: "
                + (f"Pri Index {primary_index}" if primary_index is not None else "")
                + (
                    ", "
                    if primary_index is not None and secondary_index is not None
                    else ""
                )
                + (
                    f"Sec Index {secondary_index}"
                    if secondary_index is not None
                    else ""
                )
                for actuator_id, actuator_type, primary_index, secondary_index in list_of_failures
                if actuator_type == "DAA"
            )

            # Combine the header and the detailed report
            error_message = (
                f"Actuators {sorted(set(failed_actuators_id))} FAILED the bump test.\n\n"
                f"SAA (Single Actuator Axes) Failures:\n{failed_saa_str or '  None'}\n"
                f"DAA (Dual Actuator Axes) Failures:\n{failed_daa_str or '  None'}"
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
