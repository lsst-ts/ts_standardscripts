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

import astropy.units as u
from astropy.time import Time
from astropy.coordinates import AltAz, ICRS, EarthLocation

from lsst.ts import salobj
from lsst.ts import scriptqueue

import SALPY_ATMCS
import SALPY_ATPtg


class ATPtgATMcsIntegration(scriptqueue.BaseScript):
    """Test integration between the ATPtg and ATMCS CSCs.

    Parameters
    ----------
    index : `int`
        Index of Script SAL component.
    """
    __test__ = False  # stop pytest from warning that this is not a test

    def __init__(self, index):
        atmcs = salobj.Remote(SALPY_ATMCS, 0)
        atptg = salobj.Remote(SALPY_ATPtg, 0)
        super().__init__(index=index,
                         descr="Test integration between ATPtg and ATMCS",
                         remotes_dict=dict(atmcs=atmcs, atptg=atptg))
        self.location = EarthLocation.from_geodetic(lon=-70.747698*u.deg,
                                                    lat=-30.244728*u.deg,
                                                    height=2663.0*u.m)

    async def configure(self, el=30, az=0, max_sep=1,
                        enable_atmcs=True, enable_atptg=True):
        """Configure the script.

        Parameters
        ----------
        el : `float`
            Approximate elevation of target (deg).
        az : `float`
            Approximate azimuth of target (deg).
        max_sep : `float`
            Maximum allowed on-sky separation between expected az/alt
            and the target az/alt computed by ATPtg (deg).
            This need not be tiny; it is meant as a sanity check.
        enable_atmcs : `bool` (optional)
            Enable the ATMCS CSC?
        enable_atptg : `bool` (optional)
            Enable the ATPtg CSC?
        """
        self.el = float(el)*u.deg
        self.az = float(az)*u.deg
        self.max_sep = max_sep*u.deg
        self.enable_atmcs = bool(enable_atmcs)
        self.enable_atptg = bool(enable_atptg)

    def assertEqual(self, what, val1, val2, more=""):
        if val1 != val2:
            raise RuntimeError(f"{what} = {val1}; should be {val2} {more}")

    async def run(self):
        self.log.setLevel(20)
        # Enable ATMCS and ATPgt, if requested, else check they are enabled
        await self.checkpoint("enable_cscs")
        if self.enable_atmcs:
            self.log.info(f"Enable ATMCS")
            await salobj.enable_csc(self.atmcs)
        else:
            data = self.atmcs.evt_summaryState.get()
            self.assertEqual("ATMCS summaryState", data.summaryState, salobj.State.ENABLED,
                             "ENABLED")
        if self.enable_atptg:
            self.log.info("Enable ATPtg")
            await salobj.enable_csc(self.atptg)
        else:
            data = self.atptg.evt_summaryState.get()
            self.assertEqual("ATPtg summaryState", data.summaryState, salobj.State.ENABLED,
                             "ENABLED")

        # Report current az/alt
        data = await self.atmcs.tel_mountEncoders.next(flush=False, timeout=1)
        self.log.info(f"telescope initial el={data.elevationCalculatedAngle}, "
                      f"az={data.azimuthCalculatedAngle}")

        await self.checkpoint("start_tracking")
        # Docker containers can have serious clock drift,
        # so just the time reported by ATPtg
        time_data = await self.atptg.tel_timeAndDate.next(flush=False, timeout=2)
        curr_time_atptg = Time(time_data.tai, format="mjd", scale="tai")
        time_err = curr_time_atptg - Time.now()
        self.log.info(f"Time error={time_err.sec:0.2f} sec")

        # Compute RA/Dec for commanded az/el
        cmd_elaz = AltAz(alt=self.el, az=self.az, obstime=curr_time_atptg.tai, location=self.location)
        cmd_radec = cmd_elaz.transform_to(ICRS)

        # Start tracking
        # TODO: remove the next line when ATPtg does this
        await self.atmcs.cmd_startTracking.start(timeout=2)
        self.atptg.cmd_raDecTarget.set(
            targetName="atptg_atmcs_integration",
            targetInstance=SALPY_ATPtg.ATPtg_shared_TargetInstances_current,
            frame=SALPY_ATPtg.ATPtg_shared_CoordFrame_icrs,
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
            rotFrame=SALPY_ATPtg.ATPtg_shared_RotFrame_target,
            rotMode=SALPY_ATPtg.ATPtg_shared_RotMode_field,
        )
        self.log.info(f"raDecTarget ra={self.atptg.cmd_raDecTarget.data.ra!r} hour; "
                      f"declination={self.atptg.cmd_raDecTarget.data.declination!r} deg")
        self.atmcs.evt_target.flush()
        ack_id = await self.atptg.cmd_raDecTarget.start(timeout=2)
        self.log.info(f"raDecTarget command result: {ack_id.ack.result}")

        # Check the target el/az
        # Use time from the target event, since that is the time at which
        # the position was specified.
        data = await self.atmcs.evt_target.next(flush=True, timeout=1)
        target_time = Time(data.time, scale="tai", format="unix")
        curr_time_local = Time.now()
        dtime = data.time - curr_time_local.tai.unix
        self.log.info(f"target event time={data.time:0.2f}; "
                      f"current tai unix ={curr_time_local.tai.unix:0.2f}; "
                      f"diff={dtime:0.2f} sec")
        self.log.info(f"desired el={self.el.value:0.2f}, az={self.az.value:0.2f}; "
                      f"target el={data.elevation:0.2f}, az={data.azimuth:0.2f} deg")
        self.log.info(f"target velocity el={data.elevationVelocity:0.4f}, az={data.azimuthVelocity:0.4f}")
        target_elaz = AltAz(alt=data.elevation*u.deg, az=data.azimuth*u.deg,
                            obstime=target_time, location=self.location)

        separation = cmd_elaz.separation(target_elaz).to(u.arcsec)
        self.log.info(f"el/az separation={separation}; max={self.max_sep}")
        if separation > self.max_sep:
            raise RuntimeError(f"az/el separation={separation} > {self.max_sep}")

        # Check that the telescope is heading towards the target
        data = await self.atmcs.tel_mountEncoders.next(flush=True, timeout=1)
        print(f"computed el={data.elevationCalculatedAngle}, az={data.azimuthCalculatedAngle}")
        curr_elaz0 = AltAz(alt=data.elevationCalculatedAngle*u.deg, az=data.azimuthCalculatedAngle*u.deg,
                           obstime=Time.now(), location=self.location)
        for i in range(5):
            data = await self.atmcs.tel_mountEncoders.next(flush=True, timeout=1)
            print(f"computed el={data.elevationCalculatedAngle}, az={data.azimuthCalculatedAngle}")
        curr_elaz1 = AltAz(alt=data.elevationCalculatedAngle*u.deg, az=data.azimuthCalculatedAngle*u.deg,
                           obstime=Time.now(), location=self.location)
        sep0 = cmd_elaz.separation(curr_elaz0).to(u.arcsec)
        sep1 = cmd_elaz.separation(curr_elaz1).to(u.arcsec)
        if sep0 <= sep1:
            raise RuntimeError(f"az/alt separation between commanded and current is not decreasing: "
                               f"sep0 = {sep0}; sep1 = {sep1}")

    def set_metadata(self, metadata):
        metadata.duration = 60  # rough estimate

    async def cleanup(self):
        # Stop tracking
        # TODO DM-17961: change to send stopTracking to ATPtg on error
        self.log.info("cleanup")
        try:
            await self.atptg.cmd_disable.start(timeout=1)
        except salobj.AckError as e:
            self.log.error(f"ATPtg disable failed with {e}")
        else:
            self.log.info("Disabled ATPtg")
        try:
            await self.atmcs.cmd_stopTracking.start(timeout=1)
        except salobj.AckError as e:
            self.log.error(f"cleanup: ATMCS stopTracking failed with {e}")
        else:
            self.log.info("Stopped tracking in ATMCS")
