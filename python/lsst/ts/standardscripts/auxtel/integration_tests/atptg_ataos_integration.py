# This file is part of ts_standardscripts
#
# Developed for the LSST Data Management System.
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

__all__ = ["ATPtgATAOSIntegration"]

import asyncio

import astropy.units as u
from astropy.time import Time
from astropy.coordinates import AltAz, ICRS, EarthLocation
import yaml

from lsst.ts import salobj
from lsst.ts.idl.enums import ATPtg


class ATPtgATAOSIntegration(salobj.BaseScript):
    """Test integration between the ATPtg and ATAOS CSCs.

    Parameters
    ----------
    index : `int`
        Index of Script SAL component.
    """

    __test__ = False  # stop pytest from warning that this is not a test

    def __init__(self, index):
        super().__init__(index=index, descr="Test integration between ATPtg and ATAOS")
        self.ataos = salobj.Remote(domain=self.domain, name="ATAOS")
        self.atptg = salobj.Remote(domain=self.domain, name="ATPtg")
        self.location = EarthLocation.from_geodetic(
            lon=-70.747698 * u.deg, lat=-30.244728 * u.deg, height=2663.0 * u.m
        )

        self.timeout = 30  # general timeout in seconds.

    @classmethod
    def get_schema(cls):
        schema_yaml = """
            $schema: http://json-schema.org/draft-07/schema#
            $id: https://github.com/lsst-ts/ts_standardscripts/auxtel/ATPtgATMcsIntegration.yaml
            title: ATPtgATMcsIntegration v1
            description: Configuration for ATPtgATMcsIntegration
            type: object
            properties:
              el:
                description: Approximate elevation of target (deg)
                type: number
                default: 30
              az:
                description: Approximate azimuth of target (deg)
                type: number
                default: 0
              enable_ataos:
                description: Enable the ATAOS CSC?
                type: boolean
                default: True
              enable_atptg:
                description: Enable the ATPtg CSC?
                type: boolean
                default: True
            required: [el, az, enable_ataos, enable_atptg]
            additionalProperties: false
        """
        return yaml.safe_load(schema_yaml)

    async def configure(self, config):
        """Configure the script.

        Parameters
        ----------
        config : `types.SimpleNamespace`
            Script configuration, as defined by `schema`.
        """
        config.el = config.el * u.deg
        config.az = config.az * u.deg
        self.config = config

    async def run(self):
        # Enable ATAOS and ATPgt, if requested, else check they are enabled
        await self.checkpoint("enable_cscs")
        if self.config.enable_ataos:
            self.log.info(f"Enable ATAOS")
            await salobj.set_summary_state(self.ataos, salobj.State.ENABLED)
        else:
            data = self.ataos.evt_summaryState.get()
            if data.summaryState != salobj.State.ENABLED:
                raise salobj.ExpectedError(
                    f"ATAOS summaryState={data.summaryState} != "
                    f"{salobj.State.ENABLED!r}"
                )

        if self.config.enable_atptg:
            self.log.info(f"Enable ATPtg")
            await salobj.set_summary_state(self.atptg, salobj.State.ENABLED)
        else:
            data = self.atptg.evt_summaryState.get()
            if data.summaryState != salobj.State.ENABLED:
                raise salobj.ExpectedError(
                    f"ATPtg summaryState={data.summaryState} != "
                    f"{salobj.State.ENABLED!r}"
                )

        await self.checkpoint("start_tracking")
        # Docker containers can have serious clock drift,
        # so just the time reported by ATPtg
        time_data = await self.atptg.tel_timeAndDate.next(
            flush=False, timeout=self.timeout
        )
        curr_time_atptg = Time(time_data.tai, format="mjd", scale="tai")
        time_err = curr_time_atptg - Time.now()
        self.log.info(f"Time error={time_err.sec:0.2f} sec")

        # Compute RA/Dec for commanded az/el
        cmd_elaz = AltAz(
            alt=self.config.el,
            az=self.config.az,
            obstime=curr_time_atptg.tai,
            location=self.location,
        )
        cmd_radec = cmd_elaz.transform_to(ICRS)

        # Start tracking
        self.atptg.cmd_raDecTarget.set(
            targetName="atptg_atmcs_integration",
            targetInstance=ATPtg.TargetInstances.CURRENT,
            frame=ATPtg.CoordFrame.ICRS,
            epoch=2000,  # should be ignored: no parallax or proper motion
            equinox=2000,  # should be ignored for ICRS
            ra=cmd_radec.ra.to_string(u.hour, decimal=True),
            declination=cmd_radec.dec.to_string(u.deg, decimal=True),
            parallax=0,
            pmRA=0,
            pmDec=0,
            rv=0,
            dRA=0,
            dDec=0,
            rotPA=0,
            rotFrame=ATPtg.RotFrame.TARGET,
            rotMode=ATPtg.RotMode.FIELD,
        )
        self.log.info(
            f"raDecTarget ra={self.atptg.cmd_raDecTarget.data.ra!r} hour; "
            f"declination={self.atptg.cmd_raDecTarget.data.declination!r} deg"
        )

        await self.atptg.cmd_raDecTarget.start(timeout=self.timeout)

        # make sure at least one current Target status was published...
        self.log.debug("Waiting for currentTargetStatus to be published.")
        target_status = await self.atptg.tel_currentTargetStatus.next(
            flush=True, timeout=self.timeout
        )
        self.log.debug(
            f"Got {target_status.demandRaString} {target_status.demandDecString}."
        )

        await self.checkpoint("apply_correction_manually")

        self.ataos.cmd_disableCorrection.set(disableAll=True)
        await self.ataos.cmd_disableCorrection.start(timeout=self.timeout)

        await self.ataos.cmd_applyCorrection.start(timeout=self.timeout)

        await self.checkpoint("enable_all_corrections")
        # Enable all corrections for ATAOS
        self.ataos.cmd_enableCorrection.set(enableAll=True)
        await self.ataos.cmd_enableCorrection.start(timeout=self.timeout)

        # Wait until ATAOS publishes that corrections where performed
        hexapod_completed = self.ataos.evt_hexapodCorrectionCompleted.next(
            flush=True, timeout=self.timeout
        )
        m1_completed = self.ataos.evt_m1CorrectionCompleted.next(
            flush=True, timeout=self.timeout
        )
        m2_completed = self.ataos.evt_m2CorrectionCompleted.next(
            flush=True, timeout=self.timeout
        )

        await asyncio.gather(hexapod_completed, m1_completed, m2_completed)

    def set_metadata(self, metadata):
        metadata.duration = 60  # rough estimate

    async def cleanup(self):
        # Stop tracking
        self.log.info("cleanup")
        try:
            await salobj.set_summary_state(self.atptg, salobj.State.DISABLED)
        except salobj.AckError as e:
            self.log.error(f"ATPtg disable failed with {e}")
        else:
            self.log.info("Disabled ATPtg")

        try:
            await salobj.set_summary_state(self.ataos, salobj.State.DISABLED)
        except salobj.AckError as e:
            self.log.error(f"ATAOS disable failed with {e}")
        else:
            self.log.info("Disabled ATAOS")
