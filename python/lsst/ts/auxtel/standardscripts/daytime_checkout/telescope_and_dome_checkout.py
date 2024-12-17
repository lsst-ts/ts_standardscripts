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

__all__ = ["TelescopeAndDomeCheckout"]

import asyncio

from lsst.ts import salobj
from lsst.ts.idl.enums.Script import ScriptState
from lsst.ts.observatory.control.auxtel.atcs import ATCS, ATCSUsages
from lsst.ts.observatory.control.utils.enums import RotType

STD_TIMEOUT = 10  # seconds


class TelescopeAndDomeCheckout(salobj.BaseScript):
    """DayTime Checkout SAL Script.

    This script performs the daytime checkout of the Auxiliary
    Telescope and Dome to ensure it is ready to be released
    for nighttime operations

    Parameters
    ----------
    index : `int`
        Index of Script SAL component.

    Notes
    -----
    **Checkpoints**

    - "Slewing Telecope without tracking...": Before slewing telescope, no dome
    motion
    - "Starting tracking test...": Starting sidereal tracking test...
    - "Slewing Dome...": Before slewing the dome, no telescope motion.
    - "Parking Telescope and Dome...": Before parking the Telescope and Dome at
    end of tests. Final Checkpoint.

    **Details**

    This script will perform daytime checkout of Telescope and Dome. It starts
    by performing a slew of the Telescope without Dome movement. Then sidereal
    tracking for the Telescope is enabled and the system is left to track for a
    few minutes. Tracking is disabled and then the Dome is commanded to move to
    a new position, without Telescope movement. Finally, the Telescope and
    Dome are returned to a park position and left enabled.
    """

    def __init__(self, index=1, add_remotes: bool = True):
        super().__init__(
            index=index,
            descr="Execute daytime checkout of AT Telescope and Dome.",
        )

        atcs_usage = ATCSUsages.All if add_remotes else ATCSUsages.DryTest

        # Instantiate atcs and latiss. We need to do this after the call to
        # super().__init__() above. We can also pass in the script domain and
        # logger to both classes so log messages generated internally are
        # published to the efd.
        self.atcs = ATCS(domain=self.domain, intended_usage=atcs_usage, log=self.log)

    @classmethod
    def get_schema(cls):
        return None

    async def configure(self, config):
        # This script does not require any configuration
        pass

    def set_metadata(self, metadata):
        """Set estimated duration of the script."""

        metadata.duration = 220

    async def run(self):
        await self.assert_feasibility()

        # Disable dome following for initial test
        await self.atcs.disable_dome_following()

        await self.checkpoint("Slewing Telecope without tracking...")

        # Test point az-el
        start_az = 0.0
        start_el = 80.0
        start_rot = 0
        await self.atcs.point_azel(az=start_az, el=start_el, rot_tel=start_rot)

        # Stop tracking
        await self.atcs.stop_tracking()

        await self.checkpoint("Starting tracking test...")

        # Test sidereal-tracking
        coord = self.atcs.radec_from_azel(az=start_az + 5, el=start_el - 5)
        await self.atcs.slew_icrs(
            coord.ra,
            coord.dec,
            rot=start_rot,
            stop_before_slew=False,
            rot_type=RotType.PhysicalSky,
        )

        # Sleep for 2 minutes to monitor sidereal tracking
        await self.atcs.check_tracking(120.0)

        # Stop tracking
        await self.atcs.stop_tracking()

        await self.checkpoint("Slewing Dome...")

        # Home the dome
        await self.atcs.home_dome()

        # Check that Dome Moves
        dome_az = await self.atcs.rem.atdome.tel_position.next(
            flush=True, timeout=STD_TIMEOUT
        )
        self.log.info(
            f"Dome currently thinks it is at an azimuth position of {dome_az.azimuthPosition} degrees."
        )

        d_az = 15
        await self.atcs.slew_dome_to(dome_az.azimuthPosition + d_az)
        dome_az = await self.atcs.rem.atdome.tel_position.next(
            flush=True, timeout=STD_TIMEOUT
        )
        self.log.info(
            f"After the commanded {d_az} degrees motion, the dome is at an"
            f" azimuth position of {dome_az.azimuthPosition} degrees"
        )

        await self.checkpoint("Parking Telescope and Dome...")

        # Move Telescope to park position
        await self.atcs.point_azel(
            target_name="Park position",
            az=self.atcs.tel_park_az,
            el=self.atcs.tel_park_el,
            rot_tel=self.atcs.tel_park_rot,
            wait_dome=False,
        )

        # Slew Dome to park position
        await self.atcs.slew_dome_to(az=self.atcs.dome_park_az)

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
