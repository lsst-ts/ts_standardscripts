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

__all__ = ["ATVentStart"]

import asyncio
import math
from typing import Any

import yaml
from lsst.ts import salobj
from lsst.ts.xml.enums.ATBuilding import FanDriveState, VentGateState


class ATVentStart(salobj.BaseScript):
    """Start dome venting for the auxiliary telescope.

    Notes
    -----
    **Checkpoints**

    * "Opening gates": Marks the start of the operation.
    * "Starting fan": After gates are opened but before the fan starts.

    **Details**

    * ATBuilding CSC must be ENABLED. If it is not enabled, the
      script will return a failure.

    * Gates to open may be specified. Currently only gate 2
      is connected to the controller. By default all
      gates will be commanded to open, but of course only
      gates that are wired into the controller will be affected.
      If an empty array is specified, no commands will be
      sent for the gates.

    * Fan frequency may be specified. To turn the fan off,
      set this to zero. If fan frequency is not specified,
      no commands will be sent to control the exhaust fan.
    """

    def __init__(self, index: int):
        super().__init__(
            index=index, descr="Start dome venting for the auxiliary telescope."
        )

        self.atbuilding_remote: salobj.Remote | None = None

        self.gates_to_open: list[int] | None = None
        self.gates_to_close: list[int] | None = None
        self.fan_frequency: float | None = None

        self.gate_wait_time = 10.0
        self.fan_drive_wait_time = 2.0
        self.sal_timeout = 10.0

    @classmethod
    def get_schema(cls) -> dict[str, Any]:
        schema_yaml = """---
            $schema: http://json-schema.org/draft-07/schema#
            $id: https://github.com/lsst-ts/ts_standardscripts/VentStart.yaml
            title: VentStart Configuration
            description: Configuration schema for the StartVents script
            type: object
            properties:
              gates_to_open:
                description: >-
                    An integer representing a single gate (0-3) or
                    an array of up to four gates (each between 0 and 3).
                default: [0, 1, 2, 3]
                oneOf:
                  - type: integer
                    minimum: 0
                    maximum: 3
                  - type: array
                    items:
                      type: integer
                      minimum: 0
                      maximum: 3
                    minItems: 0
                    maxItems: 4

              fan_frequency:
                description: The fan frequency in Hz.
                type: number
                minimum: 0

            additionalProperties: false
        """
        return yaml.safe_load(schema_yaml)

    async def configure(self, config):
        """Configure the script.

        Specify the gates to open and the desired fan frequency.

        Parameters
        ----------
        config : `types.SimpleNamespace`
            Configuration with two attributes:

            * gates_to_open: an integer or list of integers
              specifying which gates to open.
            * fan_frequency : a non-negative float specifying
              the target exhaust fan frequency.
        """
        self.log.info("Configure started")

        gates_to_open = getattr(config, "gates_to_open", 2)
        if isinstance(gates_to_open, int):
            gates_to_open = [gates_to_open]

        self.gates_to_close = list(set(range(4)) - set(gates_to_open))
        self.gates_to_close += [-1] * (4 - len(self.gates_to_close))

        if len(gates_to_open) == 0:
            self.gates_to_open = None
        else:
            self.gates_to_open = gates_to_open + [-1] * (4 - len(gates_to_open))

        self.fan_frequency = getattr(config, "fan_frequency", None)

        if self.atbuilding_remote is None:
            self.atbuilding_remote = salobj.Remote(
                domain=self.domain, name="ATBuilding"
            )
            await self.atbuilding_remote.start_task

    def set_metadata(self, metadata):
        """Provide estimated duration.

        The estimated duration includes:
         * Construction of a `salobj.Remote` object.
         * Opening/closing time for the vent gates.
         * Wait time to see the fan drive respond.
        """
        # Most of the duration is the salobj.Remote start time, although
        # the dome vent gates are also a bit slow to open and close.
        metadata.duration = 35.0

    async def run(self):
        """Run script."""

        # Make sure the ATBuilding CSC is ENABLED...
        summary_state = (
            await self.atbuilding_remote.evt_summaryState.aget(timeout=self.sal_timeout)
        ).summaryState
        if summary_state != salobj.State.ENABLED:
            raise RuntimeError("ATBuilding CSC must be ENABLED.")

        await self.checkpoint("Opening gates")

        if self.gates_to_open is not None:
            # Open/close the gates...
            async with asyncio.TaskGroup() as tg:
                tg.create_task(
                    self.atbuilding_remote.cmd_openVentGate.set_start(
                        gate=self.gates_to_open
                    )
                )
                tg.create_task(
                    self.atbuilding_remote.cmd_closeVentGate.set_start(
                        gate=self.gates_to_close
                    )
                )

            # TODO: DM-49084, blocked by SUMMIT-8827
            # The SAL script should wait until the vent gates are in their
            # desired state. This is not currently possible because the limit
            # switch on gate number 2 is not functional. In the interim, we
            # sleep and assume at the end that the gate is opened as long as
            # it isn't closed.
            await asyncio.sleep(self.gate_wait_time)

            # Check that the gates are in the desired state. This check allows
            # partially open gates to pass. This (1) gets around the problem
            # created by SUMMIT-8827 and (2) allows for gates that are not
            # wired.
            gate_states = (
                await self.atbuilding_remote.evt_ventGateState.aget(
                    timeout=self.sal_timeout
                )
            ).state
            for index, gate_state in enumerate(gate_states):
                if index in self.gates_to_open and gate_state == VentGateState.CLOSED:
                    raise RuntimeError(f"Gate {index} did not open as expected.")

                if index in self.gates_to_close and gate_state == VentGateState.OPENED:
                    raise RuntimeError(f"Gate {index} did not close as expected.")

        await self.checkpoint("Starting fan")

        if self.fan_frequency is not None:
            maximum_frequency = (
                await self.atbuilding_remote.evt_maximumDriveFrequency.aget(
                    timeout=self.sal_timeout
                )
            ).driveFrequency
            if self.fan_frequency > maximum_frequency:
                raise ValueError(
                    f"Requested frequency {self.fan_frequency} exceeds "
                    f"maximum of {maximum_frequency}."
                )

            await self.atbuilding_remote.cmd_setExtractionFanManualControlMode.set_start(
                enableManualControlMode=False
            )
            await self.atbuilding_remote.cmd_startExtractionFan.set_start()
            await self.atbuilding_remote.cmd_setExtractionFanDriveFreq.set_start(
                targetFrequency=self.fan_frequency
            )

            # Wait for the drive to ramp up.
            await asyncio.sleep(self.fan_drive_wait_time)

            # Verify the drive state.
            drive_state = (
                await self.atbuilding_remote.evt_extractionFanDriveState.aget(
                    timeout=self.sal_timeout
                )
            ).state
            if drive_state != FanDriveState.OPERATING:
                raise RuntimeError(f"Fan drive state incorrect: {drive_state.name}")

            drive_frequency = (
                await self.atbuilding_remote.tel_extractionFan.aget(
                    timeout=self.sal_timeout
                )
            ).driveFrequency
            if not math.isclose(self.fan_frequency, drive_frequency, abs_tol=0.1):
                raise RuntimeError(
                    f"Drive frequency ({drive_frequency}) does not match requested value {self.fan_frequency}"
                )
