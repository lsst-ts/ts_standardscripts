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

__all__ = ["ATPtgATMcsIntegration"]

import asyncio

import astropy.units as u
from astropy.time import Time
from astropy.coordinates import AltAz, ICRS, EarthLocation, Angle
import yaml

from lsst.ts import salobj
from lsst.ts.idl.enums import ATPtg


class ATPtgATMcsIntegration(salobj.BaseScript):
    """Test integration between the ATPtg and ATMCS CSCs.

    Parameters
    ----------
    index : `int`
        Index of Script SAL component.
    """

    __test__ = False  # stop pytest from warning that this is not a test

    def __init__(self, index):
        super().__init__(index=index, descr="Test integration between ATPtg and ATMCS")
        self.atmcs = salobj.Remote(domain=self.domain, name="ATMCS")
        self.atptg = salobj.Remote(domain=self.domain, name="ATPtg")
        self.location = EarthLocation.from_geodetic(
            lon=-70.747698 * u.deg, lat=-30.244728 * u.deg, height=2663.0 * u.m
        )

        self.poll_time = 10.0  # wait time in tracking test loop (seconds)

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
                default: 45
              az:
                description: Approximate azimuth of target (deg)
                type: number
                default: 45
              max_sep:
                description: Maximum allowed on-sky separation between expected az/alt
                  and the target az/alt computed by ATPtg (deg).
                  This need not be tiny; it is meant as a sanity check.
                type: number
                default: 1
              track_duration:
                description: How long to track after slewing to position (hour).
                type: number
                default: 0.02
              max_track_error:
                description: Maximum allowed on-sky separation between commanded
                  and measured az/el (arcsec).
                type: number
                default: 5
              enable_atmcs:
                description: Enable the ATMCS CSC?
                type: boolean
                default: True
              enable_atptg:
                description: Enable the ATPtg CSC?
                type: boolean
                default: True
            required: [el, az, max_sep, track_duration, max_track_error, enable_atmcs, enable_atptg]
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
        units_dict = dict(
            el=u.deg,
            az=u.deg,
            max_sep=u.deg,
            track_duration=u.hour,
            max_track_error=u.arcsec,
        )
        for field, units in units_dict.items():
            setattr(config, field, getattr(config, field) * units)
        self.config = config

    async def run(self):
        # Enable ATMCS and ATPgt, if requested, else check they are enabled
        await self.checkpoint("enable_cscs")
        if self.config.enable_atmcs:
            self.log.info(f"Enable ATMCS")
            await salobj.set_summary_state(self.atmcs, salobj.State.ENABLED)
        else:
            data = self.atmcs.evt_summaryState.get()
            if data.summaryState != salobj.State.ENABLED:
                raise salobj.ExpectedError(
                    f"ATMCS summaryState={data.summaryState} != "
                    f"{salobj.State.ENABLED!r}"
                )
        if self.config.enable_atptg:
            self.log.info("Enable ATPtg")
            await salobj.set_summary_state(self.atptg, salobj.State.ENABLED)
        else:
            data = self.atptg.evt_summaryState.get()
            if data.summaryState != salobj.State.ENABLED:
                raise salobj.ExpectedError(
                    f"ATPtg summaryState={data.summaryState} != "
                    f"{salobj.State.ENABLED!r}"
                )

        # Report current az/alt
        data = await self.atmcs.tel_mountEncoders.next(flush=False, timeout=1)
        self.log.info(
            f"telescope initial el={data.elevationCalculatedAngle}, "
            f"az={data.azimuthCalculatedAngle}"
        )

        await self.checkpoint("start_tracking")
        # Docker containers can have serious clock drift,
        # so just the time reported by ATPtg
        time_data = await self.atptg.tel_timeAndDate.next(flush=False, timeout=2)
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
            ra=cmd_radec.ra.hour,
            declination=cmd_radec.dec.deg,
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
        self.atmcs.evt_target.flush()
        self.atmcs.evt_allAxesInPosition.flush()
        ack_id = await self.atptg.cmd_raDecTarget.start(timeout=2)
        self.log.info(f"raDecTarget command result: {ack_id.ack.result}")

        # Check the target el/az
        # Use time from the target event, since that is the time at which
        # the position was specified.
        data = await self.atmcs.evt_target.next(flush=True, timeout=1)
        event_tai = data.taiTime
        target_time = Time(event_tai, scale="tai", format="unix")
        curr_time_local = Time.now()
        dtime = event_tai - curr_time_local.tai.unix
        self.log.info(
            f"target event time={event_tai:0.2f}; "
            f"current tai unix ={curr_time_local.tai.unix:0.2f}; "
            f"diff={dtime:0.2f} sec"
        )
        self.log.info(
            f"desired el={self.config.el.value:0.2f}, az={self.config.az.value:0.2f}; "
            f"target el={data.elevation:0.2f}, az={data.azimuth:0.2f} deg"
        )
        self.log.info(
            f"target velocity el={data.elevationVelocity:0.4f}, az={data.azimuthVelocity:0.4f}"
        )
        target_elaz = AltAz(
            alt=data.elevation * u.deg,
            az=data.azimuth * u.deg,
            obstime=target_time,
            location=self.location,
        )

        separation = cmd_elaz.separation(target_elaz).to(u.arcsec)
        self.log.info(f"el/az separation={separation}; max={self.config.max_sep}")
        if separation > self.config.max_sep:
            raise RuntimeError(f"az/el separation={separation} > {self.config.max_sep}")

        # Check that the telescope is heading towards the target
        data = await self.atmcs.tel_mountEncoders.next(flush=True, timeout=1)
        print(
            f"computed el={data.elevationCalculatedAngle}, az={data.azimuthCalculatedAngle}"
        )
        curr_elaz0 = AltAz(
            alt=data.elevationCalculatedAngle * u.deg,
            az=data.azimuthCalculatedAngle * u.deg,
            obstime=Time.now(),
            location=self.location,
        )
        for i in range(5):
            data = await self.atmcs.tel_mountEncoders.next(flush=True, timeout=1)
            print(
                f"computed el={data.elevationCalculatedAngle}, az={data.azimuthCalculatedAngle}"
            )
        curr_elaz1 = AltAz(
            alt=data.elevationCalculatedAngle * u.deg,
            az=data.azimuthCalculatedAngle * u.deg,
            obstime=Time.now(),
            location=self.location,
        )
        sep0 = cmd_elaz.separation(curr_elaz0).to(u.arcsec)
        sep1 = cmd_elaz.separation(curr_elaz1).to(u.arcsec)
        if sep0 <= sep1:
            raise RuntimeError(
                f"az/alt separation between commanded and current is not "
                f"decreasing: sep0 = {sep0}; sep1 = {sep1}"
            )

        # Monitor tracking for the specified duration

        if self.config.track_duration == 0.0:
            self.log.info("Skipping track test...")
            return

        self.log.info(
            f"Monitoring tracking for {self.config.track_duration}. Wait for "
            f"allAxesInPosition event."
        )
        while True:
            in_position = await self.atmcs.evt_allAxesInPosition.next(
                flush=False, timeout=10
            )
            self.log.debug(f"Got {in_position.inPosition}")
            if in_position.inPosition:
                break

        start_time = Time.now()

        while Time.now() - start_time < self.config.track_duration:

            mount_data = await self.atmcs.tel_mountEncoders.next(flush=True, timeout=1)
            current_target = await self.atptg.tel_currentTargetStatus.next(
                flush=True, timeout=1
            )

            mount_azel = AltAz(
                alt=mount_data.elevationCalculatedAngle * u.deg,
                az=mount_data.azimuthCalculatedAngle * u.deg,
                obstime=Time.now(),
                location=self.location,
            )

            demand_azel = AltAz(
                alt=Angle(current_target.demandEl, unit=u.deg),
                az=Angle(current_target.demandAz, unit=u.deg),
                obstime=Time.now(),
                location=self.location,
            )

            self.log.info(f"Mount: el={mount_azel.alt}, " f"az={mount_azel.az}")

            self.log.info(
                f"ATPtg demand: el={demand_azel.alt}, " f"az={demand_azel.az}"
            )

            track_error = mount_azel.separation(demand_azel).to(u.arcsec)
            self.log.info(f"Track error: {track_error}")

            if track_error > self.config.max_track_error:
                raise RuntimeError(
                    f"Track error={track_error} > {self.config.max_track_error}"
                )
            else:
                self.log.info(
                    f"Track error={track_error}; max={self.config.max_track_error}"
                )

            await asyncio.sleep(self.poll_time)

    def set_metadata(self, metadata):
        metadata.duration = 60  # rough estimate

    async def cleanup(self):
        # Stop tracking
        self.log.info("cleanup")
        try:
            await self.atptg.cmd_stopTracking.start(timeout=1)
        except salobj.AckError as e:
            self.log.error(f"ATPtg stopTracking failed with {e}")
        else:
            self.log.info("Tracking stopped")
