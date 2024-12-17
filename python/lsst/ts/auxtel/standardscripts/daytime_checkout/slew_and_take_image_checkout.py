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

__all__ = ["SlewAndTakeImageCheckout"]

import asyncio

from lsst.ts import salobj
from lsst.ts.idl.enums.ATMCS import M3State
from lsst.ts.idl.enums.Script import ScriptState
from lsst.ts.observatory.control.auxtel.atcs import ATCS, ATCSUsages
from lsst.ts.observatory.control.auxtel.latiss import LATISS, LATISSUsages
from lsst.ts.observatory.control.utils.enums import RotType
from lsst.ts.standardscripts.utils import get_topic_time_utc

STD_TIMEOUT = 10  # seconds


class SlewAndTakeImageCheckout(salobj.BaseScript):
    """DayTime Slew and Take Image Checkout SAL Script.

    This script performs the daytime checkout of
    LATISS to ensure it is ready to be released
    for nighttime operations

    Parameters
    ----------
    index : `int`
        Index of Script SAL component.

    Notes
    -----
    **Checkpoints**

    - "Slew and take image 1/2": Before slewing to first target. Dome and
    Sidereal tracking are enabled. Target will track for three minutes.
    - "Slew and take image 2/2": Before slewing to second target. Dome and
    Sidereal tracking are enabled. Target will track for three minutes.
    - "Stopping tracking, parking Telescope and Dome...": Before parking the
    telescope and dome at end of tests. Final Checkpoint.

    **Details**

    This script is used to perform the daytime checkout of the full AuxTel
    system to ensure it is ready for nighttime operation. It builds on previous
    checkouts and performs Telescope and Dome slews and verification images
    as well as tracking. The Telescope and Dome are left in their parked
    positions at the end of the chckout and the mirror covers remain closed
    during the entire test.
    """

    def __init__(self, index=1, add_remotes: bool = True):
        super().__init__(
            index=index,
            descr="Execute daytime checkout of AT and LATISS.",
        )

        latiss_usage = None if add_remotes else LATISSUsages.DryTest

        atcs_usage = None if add_remotes else ATCSUsages.DryTest

        # Instantiate latiss. We need to do this after the call to
        # super().__init__() above. We can also pass in the script domain and
        # logger to both classes so log messages generated internally are
        # published to the efd.
        self.atcs = ATCS(domain=self.domain, intended_usage=atcs_usage, log=self.log)

        tcs_ready_to_take_data = self.atcs.ready_to_take_data if add_remotes else None
        self.latiss = LATISS(
            domain=self.domain,
            intended_usage=latiss_usage,
            log=self.log,
            tcs_ready_to_take_data=tcs_ready_to_take_data,
        )

    @classmethod
    def get_schema(cls):
        return None

    async def configure(self, config):
        # This script does not require any configuration
        pass

    def set_metadata(self, metadata):
        """Set estimated duration of the script."""

        metadata.duration = 410

    async def run(self):
        await self.assert_feasibility()

        # Check that m3 is in position and Port 2 is selected.
        m3_state = await self.atcs.rem.atmcs.evt_m3State.aget()
        if m3_state.state == M3State.NASMYTH2:
            self.log.info(f"M3 is ready in position at port -- {M3State.NASMYTH2}")
        else:
            raise RuntimeError(
                f"M3 is NOT in position for observations with LATISS. M3_state is {m3_state.state} "
                f"and must be {M3State.NASMYTH2}. Check that M3 is in correct position and is not moving."
            )

        # Ensure mirrors and vents are closed for safer operations
        await self.atcs.close_m1_cover()
        await self.atcs.close_m1_vent()

        # Enable Dome following to allow dome to slew with telescope
        await self.atcs.enable_dome_following()

        # Turn on ATAOS correction(s)
        cmd = await self.atcs.rem.ataos.cmd_enableCorrection.set_start(
            m1=True, hexapod=True, atspectrograph=True
        )
        cmd_time = get_topic_time_utc(cmd)
        self.log.info(f"ATAOS corrections enabled -- {cmd.result} at {cmd_time} UT")

        # Now slew to a new position and start tracking a siderial target.
        start_az = 45
        start_el = 45
        start_rot = 0
        coord = self.atcs.radec_from_azel(az=start_az, el=start_el)
        await self.atcs.slew_icrs(
            coord.ra,
            coord.dec,
            rot=start_rot,
            rot_type=RotType.PhysicalSky,
            target_name="DaytimeCheckout001",
        )

        # Take an Engineering test frame and verify ingestion at OODS
        await self.checkpoint("Slew and take image 1/2")

        self.latiss.rem.atoods.evt_imageInOODS.flush()
        await self.latiss.take_engtest(2, filter=0, grating=0)
        try:
            ingest_event = await self.latiss.rem.atoods.evt_imageInOODS.next(
                flush=False, timeout=STD_TIMEOUT
            )
        except asyncio.TimeoutError:
            raise RuntimeError(
                "Timeout waiting for imageInOODS event for image 1/2. This "
                "usually means there is a problem with the image ingestion."
            )

        assert ingest_event.statusCode == 0, "Image ingestion 1/2 was not successful!"

        ingest_event_time = get_topic_time_utc(ingest_event)
        inst_setup = await self.latiss.get_setup()
        self.log.info(
            f"Image 1/2 with id {ingest_event.obsid} was ingested at "
            f"{ingest_event_time.utc} UT with {inst_setup[0]} filter "
            f"and {inst_setup[1]} grating"
        )

        # Pause and let it track for a few minutes
        await self.atcs.check_tracking(120.0)

        await self.checkpoint("Slew and take image 2/2")

        # Slew to a second target and repeat
        start_az = 0.0
        start_el = 80
        start_rot = 0
        coord = self.atcs.radec_from_azel(az=start_az, el=start_el)
        await self.atcs.slew_icrs(
            coord.ra,
            coord.dec,
            rot=start_rot,
            rot_type=RotType.PhysicalSky,
            target_name="DaytimeCheckout002",
        )

        # Take an Engineering test frame and verify ingestion at OODS
        self.latiss.rem.atoods.evt_imageInOODS.flush()
        await self.latiss.take_engtest(2, filter=1, grating=1)
        try:
            ingest_event = await self.latiss.rem.atoods.evt_imageInOODS.next(
                flush=False, timeout=STD_TIMEOUT
            )
        except asyncio.TimeoutError:
            raise RuntimeError(
                "Timeout waiting for imageInOODS event for image 2/2. This "
                "usually means there is a problem with the image ingestion."
            )

        assert ingest_event.statusCode == 0, "Ingestion was not successful!"

        ingest_event_time = get_topic_time_utc(ingest_event)
        inst_setup = await self.latiss.get_setup()
        self.log.info(
            f"Image 2/2 with id {ingest_event.obsid} was ingested at"
            f"{ingest_event_time.utc} UT with {inst_setup[0]} filter"
            f"and {inst_setup[1]} grating "
        )

        # Pause and let it track for a few minutes
        await self.atcs.check_tracking(120.0)

        await self.checkpoint("Stopping tracking, parking Telescope and Dome")

        # Stop tracking
        await self.atcs.stop_tracking()

        # Disable Dome Following
        await self.atcs.disable_dome_following()

        # Move Telescope to park position
        await self.atcs.point_azel(
            target_name="Park position",
            az=self.atcs.tel_park_az,
            el=self.atcs.tel_park_el,
            rot_tel=self.atcs.tel_park_rot,
        )

        # Stop tracking after point_azel
        await self.atcs.stop_tracking()

        # Slew Dome to park position
        await self.atcs.slew_dome_to(az=self.atcs.dome_park_az)

    async def assert_feasibility(self):
        """Verify that the system is in a feasible state to execute the
        script.
        """
        await asyncio.gather(
            self.atcs.assert_all_enabled(),
            self.latiss.assert_all_enabled(),
        )

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
