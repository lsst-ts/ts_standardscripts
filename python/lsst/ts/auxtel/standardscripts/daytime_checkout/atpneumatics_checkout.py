# This file is part of ts_auxtel_standardscripts
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

__all__ = ["ATPneumaticsCheckout"]

import asyncio

from lsst.ts import salobj
from lsst.ts.idl.enums.Script import ScriptState
from lsst.ts.observatory.control.auxtel.atcs import ATCS

STD_TIMEOUT = 5  # seconds


class ATPneumaticsCheckout(salobj.BaseScript):
    """Pneumatics Checkout SAL Script.

    This script performs the daytime checkout of the Auxiliary
    Telescope pneumatics system to ensure it is ready to be released
    for nighttime operations.

    Parameters
    ----------
    index : `int`
        Index of Script SAL component.

    Notes
    -----
    **Checkpoints**

    - "Opening pneumatics valves": Before opening pneumatics valves, this will
    pressurize the system.
    - "Turning on ATAOS coerrections": Before turning on ATAOS corrections.
    - "Turning off ATAOS coerrections": Before turning off ATAOS corrections.
    - "Lowering Mirror to hardpoints": Before lowering mirror to hardpoints.
    - "Exercising Mirror Covers and Vents": Before opening and closing the
    mirror covers and vents, final checkpoint in script.

    **Details**

    This script performs a daytime checkout of the Auxiliary Telescope
    Pneumatics system. It will first slew the Telescope to the park position.
    Next, it will turn on the valves and check that the line pressure is
    sufficient for operations. Then, it will turn on/off the ATAOS corrections
    before lowering the mirror back down onto its hardpoints. Finally the
    mirror cover and vents are opened and closed.
    """

    def __init__(self, index=1):
        super().__init__(
            index=index,
            descr="Execute daytime checkout of AT Pneumatics.",
        )

        self.atcs = None

        self.main_air_pressure_min_threshold = 275790
        self.main_air_pressure_max_threshold = 413000
        self.delay_ataos_enabled = 10
        self.delay_ataos_disabled = 15
        self.pressure_tolerance_relative = 0.03
        self.pressure_ataos_enabled_floor = 30000

    @classmethod
    def get_schema(cls):
        return None

    async def configure(self, config):
        # This script does not require any configuration
        if self.atcs is None:
            self.atcs = ATCS(domain=self.domain, log=self.log)
            await self.atcs.start_task

    def set_metadata(self, metadata):
        """Set estimated duration of the script."""

        metadata.duration = 95

    async def run(self):
        await self.assert_feasibility()

        await self.checkpoint("Slewing Telescope to park position")

        # Move Telescope to park position
        await self.atcs.point_azel(
            target_name="Park position",
            az=self.atcs.tel_park_az,
            el=self.atcs.tel_park_el,
            rot_tel=self.atcs.tel_park_rot,
        )

        await self.checkpoint("Opening pneumatics valves")

        await self.atcs.open_valves()
        pressure = await self.atcs.rem.atpneumatics.tel_mainAirSourcePressure.next(
            flush=True, timeout=STD_TIMEOUT
        )
        if (
            self.main_air_pressure_min_threshold
            < pressure.pressure
            < self.main_air_pressure_max_threshold
        ):
            self.log.info(
                f"Air pressure is {pressure.pressure:0.0f} Pascals, which is fine."
            )
        else:
            raise RuntimeError(
                f"Air pressure is {pressure.pressure:0.0f}, outside acceptable range. "
                f"It needs to be between {self.main_air_pressure_min_threshold} and "
                f"{self.main_air_pressure_max_threshold} \n Check that compressor and "
                "dryer are running. Then check that the regulator inside the pier is set correctly. "
            )

        # Turn on ATAOS correction(s).

        await self.checkpoint("Turning on ATAOS corrections")

        await self.atcs.enable_ataos_corrections()

        # Sleep to allow M1 to arrive at commanded pressure
        await asyncio.sleep(self.delay_ataos_enabled)

        m1_commanded_pressure = (
            await self.atcs.rem.ataos.evt_m1CorrectionCompleted.aget(
                timeout=STD_TIMEOUT
            )
        )

        m1_pressure = await self.atcs.rem.atpneumatics.tel_m1AirPressure.aget(
            timeout=STD_TIMEOUT
        )

        # Check that M1 pressure arrived to ATAOS commanded pressure within
        # tolerance
        if (
            m1_commanded_pressure.pressure * (1.0 - self.pressure_tolerance_relative)
            < m1_pressure.pressure
            < m1_commanded_pressure.pressure * (1.0 + self.pressure_tolerance_relative)
        ):
            self.log.info(
                f"M1 Air pressure with enabled ATOAS corrections is {m1_pressure.pressure:0.0f} Pascals."
            )
        else:
            raise RuntimeError(
                "M1 air pressure failed to arrive at desired value of"
                f"({m1_commanded_pressure:0.0f}+/-"
                f"{self.pressure_tolerance_relative*m1_commanded_pressure:0.0f})"
                f"within specified time limit of {self.delay_ataos_enabled}s. Recorded M1 air pressure is "
                f"{m1_pressure.pressure:0.0f} Pascals."
            )

        await self.checkpoint("Turning off ATAOS corrections")

        # Turn off ATAOS correction(s)
        await self.atcs.disable_ataos_corrections()

        # Sleep to allow M1 to settle down to hard points
        await asyncio.sleep(self.delay_ataos_disabled)

        m1_pressure = await self.atcs.rem.atpneumatics.tel_m1AirPressure.aget(
            timeout=STD_TIMEOUT
        )

        # Check that M1 pressure below floor with ATAOS corrections disabled.
        if m1_pressure.pressure < self.pressure_ataos_enabled_floor:
            self.log.info(
                f"M1 air pressure after ATAOS corrections disabled is {m1_pressure.pressure:0.0f} Pascals"
            )
        else:
            raise RuntimeError(
                f"M1 Air pressure {self.delay_ataos_disabled}s after ATAOS corrections disabled is "
                f"{m1_pressure.pressure:0.0f} Pascals, which is above acceptable limit of "
                f"{self.pressure_ataos_enabled_floor:0.0f} Pascals."
            )

        await self.checkpoint("Exercising Mirror Covers and Vents")

        # Open mirror covers and vents
        await self.atcs.open_m1_cover()
        await self.atcs.open_m1_vent()

        # Close mirror covers and vents
        await self.atcs.close_m1_cover()
        await self.atcs.close_m1_vent()

    async def assert_feasibility(self):
        """Verify that the system is in a feasible state to execute the
        script.
        """
        await self.atcs.assert_all_enabled()

    async def cleanup(self):
        if self.state.state != ScriptState.ENDING:
            try:
                await self.atcs.stop_tracking()
            except asyncio.TimeoutError:
                self.log.exception(
                    "Stop tracking command timed out during cleanup procedure."
                )
            except Exception:
                self.log.exception("Unexpected exception in stop_tracking.")

            try:
                await self.atcs.disable_ataos_corrections()
            except Exception:
                self.log.exception("Unexpected exception disabling ataos corrections.")
