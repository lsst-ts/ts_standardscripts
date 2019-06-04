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

__all__ = ["ATSlewing"]

import yaml
import asyncio
import logging


import astropy.units as u
from astropy.time import Time
from astropy.coordinates import AltAz, ICRS, EarthLocation
from math import isclose

from lsst.ts import salobj
from lsst.ts import scriptqueue

import SALPY_ATMCS
import SALPY_ATPtg
import SALPY_ATAOS
import SALPY_ATHexapod
import SALPY_ATPneumatics


class ATSlewing(scriptqueue.BaseScript):

    def __init__(self, index):
        atmcs = salobj.Remote(SALPY_ATMCS, 0)
        atptg = salobj.Remote(SALPY_ATPtg, 0)
        ataos = salobj.Remote(SALPY_ATAOS)
        athexapod = salobj.Remote(SALPY_ATHexapod)
        atpneumatics = salobj.Remote(SALPY_ATPneumatics)
        self.timeout = 5
        self.tolerance = 0.5
        super().__init__(index=index,
                         descr="integration test for components involved in slewing operations",
                         remotes_dict=dict(atmcs=atmcs,
                                           atptg=atptg,
                                           ataos=ataos,
                                           athexapod=athexapod,
                                           atpneumatics=atpneumatics))
        self.location = EarthLocation.from_geodetic(lon=-70.747698*u.deg,
                                                    lat=-30.244728*u.deg,
                                                    height=2663.0*u.m)
        self.pool_time = 10.  # wait time in tracking test loop (seconds)

    async def configure(self,
                        startEl=45.,
                        startAz=45.,
                        endEl=75.,
                        endAz=135.,
                        max_sep=1.,
                        enable_atmcs=True,
                        enable_atptg=True,
                        enable_ataos=True,
                        enable_athexapod=True,
                        enable_atpneumatics=True):
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
        self.startEl = float(startEl)*u.deg
        self.startAz = float(startAz)*u.deg
        self.endEl = float(endEl)*u.deg
        self.endAz = float(endAz)*u.deg
        self.max_sep = float(max_sep)*u.deg
        self.enable_atmcs = bool(enable_atmcs)
        self.enable_atptg = bool(enable_atptg)
        self.enable_ataos = bool(enable_ataos)
        self.enable_athexapod = bool(enable_athexapod)
        self.enable_atpneumatics = bool(enable_atpneumatics)

    def assertEqual(self, what, val1, val2, more=""):
        if val1 != val2:
            raise RuntimeError(f"{what} = {val1}; should be {val2} {more}")

    async def run(self):
        # Enable ATMCS and ATPgt, if requested, else check they are enabled
        print("here")
        await self.checkpoint("enable_cscs")
        print("waited for csc enables")
        if self.enable_atmcs:
            self.log.info(f"Enable ATMCS")
            await salobj.set_summary_state(self.atmcs, salobj.State.ENABLED)
        else:
            data = await self.atmcs.evt_summaryState.next(flush=False, timeout=self.timeout)
            self.assertEqual("ATMCS summaryState", data.summaryState, salobj.State.ENABLED,
                             "ENABLED")
        if self.enable_atptg:
            self.log.info("Enable ATPtg")
            await salobj.enable_csc(self.atptg)
        else:
            data = await self.atptg.evt_summaryState.next(flush=False, timeout=self.timeout)
            self.assertEqual("ATPtg summaryState", data.summaryState, salobj.State.ENABLED,
                             "ENABLED")
        if self.enable_ataos:
            self.log.info("Enable ATAOS")
            await salobj.enable_csc(self.ataos)
        else:
            data = await self.ataos.evt_summaryState.next(flush=False, timeout=self.timeout)
            self.assertEqual("ATAOS summaryState",
                             data.summaryState,
                             salobj.State.ENABLED,
                             "ENABLED")
        if self.enable_athexapod:
            self.log.info("Enable ATHexapod")
            await salobj.enable_csc(self.athexapod)
        else:
            data = await self.athexapod.evt_summaryState.next(flush=False, timeout=self.timeout)
            self.assertEqual("ATHexapod summaryState",
                             data.summaryState,
                             salobj.State.ENABLED,
                             "ENABLED")
        if self.enable_atpneumatics:
            self.log.info("Enable ATPneumatics")
            await salobj.enable_csc(self.atpneumatics)
        else:
            data = await self.atpneumatics.evt_summaryState.next(flush=False, timeout=self.timeout)
            self.assertEqual("ATPneumatics summaryState",
                             data.summaryState,
                             salobj.State.ENABLED,
                             "ENABLED")

        # Report current az/alt
        self.log.debug("here")
        data = await self.atmcs.tel_mountEncoders.next(flush=False, timeout=1)
        self.log.info(f"telescope initial el={data.elevationCalculatedAngle}, "
                      f"az={data.azimuthCalculatedAngle}")

        await self.checkpoint("start_slewing")
        # Docker containers can have serious clock drift,
        # so just the time reported by ATPtg
        time_data = await self.atptg.tel_timeAndDate.next(flush=False, timeout=2)
        curr_time_atptg = Time(time_data.tai, format="mjd", scale="tai")
        time_err = curr_time_atptg - Time.now()
        self.log.info(f"Time error={time_err.sec:0.2f} sec")

        # Compute RA/Dec for starting az/el
        cmd_startelaz = AltAz(alt=self.startEl, az=self.startAz, obstime=curr_time_atptg.tai,
                              location=self.location)
        cmd_startradec = cmd_startelaz.transform_to(ICRS)

        # Compute RA/Dec for ending az/el
        cmd_endelaz = AltAz(alt=self.endEl, az=self.endAz, obstime=curr_time_atptg.tai,
                            location=self.location)
        cmd_endradec = cmd_endelaz.transform_to(ICRS)

        # move to starting position
        print("move to starting position")
        self.atptg.cmd_raDecTarget.set(
            targetName="slew_integration_startposition",
            targetInstance=SALPY_ATPtg.ATPtg_shared_TargetInstances_current,
            frame=SALPY_ATPtg.ATPtg_shared_CoordFrame_icrs,
            epoch=2000,  # should be ignored: no parallax or proper motion
            equinox=2000,  # should be ignored for ICRS
            ra=cmd_startradec.ra.hour,
            declination=cmd_startradec.dec.deg,
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
        self.log.info(f"raDecTargetStart ra={self.atptg.cmd_raDecTarget.data.ra!r} hour; "
                      f"declination={self.atptg.cmd_raDecTarget.data.declination!r} deg")
        self.atmcs.evt_target.flush()
        self.atmcs.evt_allAxesInPosition.flush()
        ack_id = await self.atptg.cmd_raDecTarget.start(timeout=2)
        self.log.info(f"raDecTarget command result: {ack_id.ack.result}")
        while True:
            in_position = await self.atmcs.evt_allAxesInPosition.next(flush=False, timeout=150)
            if in_position.inPosition:
                self.log.info("finished slew to start pos")
                break
        await asyncio.sleep(10)
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
        self.log.info(f"desired starting el={self.startEl.value:0.2f}, az={self.startAz.value:0.2f}; "
                      f"target el={data.elevation:0.2f}, az={data.azimuth:0.2f} deg")
        self.log.info(f"target velocity el={data.elevationVelocity:0.4f}, az={data.azimuthVelocity:0.4f}")
        target_elaz = AltAz(alt=data.elevation*u.deg, az=data.azimuth*u.deg,
                            obstime=target_time, location=self.location)

        separation = cmd_startelaz.separation(target_elaz).to(u.arcsec)
        self.log.info(f"el/az separation={separation}; max={self.max_sep}")
        if separation > self.max_sep:
            raise RuntimeError(f"az/el separation={separation} > {self.max_sep}")

        # Check that the telescope is heading towards the target
        data = await self.atmcs.tel_mountEncoders.next(flush=True, timeout=1)
        print(f"computed el={data.elevationCalculatedAngle}, az={data.azimuthCalculatedAngle}")
        for i in range(5):
            data = await self.atmcs.tel_mountEncoders.next(flush=True, timeout=1)
            print(f"computed el={data.elevationCalculatedAngle}, az={data.azimuthCalculatedAngle}")
        # enable ATAOS correction loop
        self.ataos.cmd_enableCorrection.set(enableAll=True)
        await self.ataos.cmd_enableCorrection.start(timeout=10)

        # move to ending position
        await self.atptg.cmd_stopTracking.start(timeout=5)
        print("moving to ending position")
        self.atptg.cmd_raDecTarget.set(
            targetName="slew_integration_endposition",
            targetInstance=SALPY_ATPtg.ATPtg_shared_TargetInstances_current,
            frame=SALPY_ATPtg.ATPtg_shared_CoordFrame_icrs,
            epoch=2000,  # should be ignored: no parallax or proper motion
            equinox=2000,  # should be ignored for ICRS
            ra=cmd_endradec.ra.hour,
            declination=cmd_endradec.dec.deg,
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
        self.log.info(f"raDecTargetEnd ra={self.atptg.cmd_raDecTarget.data.ra!r} hour; "
                      f"declination={self.atptg.cmd_raDecTarget.data.declination!r} deg")
        self.atmcs.evt_target.flush()
        self.atmcs.evt_allAxesInPosition.flush()
        ack_id = await self.atptg.cmd_raDecTarget.start(timeout=2)
        self.log.info(f"raDecTarget command result: {ack_id.ack.result}")
        while True:
            in_position = await self.atmcs.evt_allAxesInPosition.next(flush=False, timeout=150)
            if in_position.inPosition:
                self.log.info("finished slew to end pos")
                break

        # Report current az/alt
        data = await self.atmcs.tel_mountEncoders.next(flush=True, timeout=1)
        self.log.info(f"telescope final el={data.elevationCalculatedAngle}, "
                      f"az={data.azimuthCalculatedAngle}")

        # Test that we are in the state we want to be in
        print("checking ATAOS events reporting az/el consistent with target")
        data = await self.ataos.evt_m1CorrectionStarted.next(flush=True, timeout=75)
        self.log.info(f"AOS M1 Correction start reported el={data.elevation}, "
                      f"az={data.azimuth}")
        assert isclose(self.endEl.value, data.elevation, abs_tol=self.tolerance)
        assert isclose(self.endAz.value, data.azimuth, abs_tol=self.tolerance)
        data = await self.ataos.evt_m1CorrectionCompleted.next(flush=True, timeout=75)
        self.log.info(f"AOS M1 Correction complete reported el={data.elevation}, "
                      f"az={data.azimuth}")
        assert isclose(self.endEl.value, data.elevation, abs_tol=self.tolerance)
        assert isclose(self.endAz.value, data.azimuth, abs_tol=self.tolerance)

        data = await self.ataos.evt_m2CorrectionStarted.next(flush=True, timeout=75)
        self.log.info(f"AOS M2 Correction start reported el={data.elevation}, "
                      f"az={data.azimuth}")
        assert isclose(self.endEl.value, data.elevation, abs_tol=self.tolerance)
        assert isclose(self.endAz.value, data.azimuth, abs_tol=self.tolerance)
        data = await self.ataos.evt_m2CorrectionCompleted.next(flush=True, timeout=75)
        self.log.info(f"AOS M2 Correction complete reported el={data.elevation}, "
                      f"az={data.azimuth}")
        assert isclose(self.endEl.value, data.elevation, abs_tol=self.tolerance)
        assert isclose(self.endAz.value, data.azimuth, abs_tol=self.tolerance)

        data = await self.ataos.evt_hexapodCorrectionStarted.next(flush=True, timeout=75)
        self.log.info(f"AOS hexapod Correction start reported el={data.elevation}, "
                      f"az={data.azimuth}")
        assert isclose(self.endEl.value, data.elevation, abs_tol=self.tolerance)
        assert isclose(self.endAz.value, data.azimuth, abs_tol=self.tolerance)
        data = await self.ataos.evt_hexapodCorrectionCompleted.next(flush=True, timeout=75)
        self.log.info(f"AOS hexapod Correction complete reported el={data.elevation}, "
                      f"az={data.azimuth}")
        assert isclose(self.endEl.value, data.elevation, abs_tol=self.tolerance)
        assert isclose(self.endAz.value, data.azimuth, abs_tol=self.tolerance)

    def set_metadata(self, metadata):
        metadata.duration = 60  # rough estimate

    async def waitForSlew(self):
        while True:
            in_position = await self.atmcs.evt_allAxesInPosition.next(flush=False, timeout=150)
            if in_position.inPosition:
                self.log.info("finished slew to end pos")
                break

    @staticmethod
    def fault_check(summary_state_evt):
        if summary_state_evt.summaryState == salobj.State.FAULT:
            self.in_fault = True

    async def cleanup(self):
        # Stop tracking
        self.log.info("cleanup")
        try:
            await self.atptg.cmd_stopTracking.start(timeout=150)
            pass
        except salobj.AckError as e:
            self.log.error(f"ATPtg stopTracking failed with {e}")
        else:
            self.log.info("Tracking stopped")


async def main():

    script = ATSlewing(index=10)

    script.log.setLevel(logging.DEBUG)
    script.log.addHandler(logging.StreamHandler())

    config_dict = dict(enable_atmcs=True, enable_atptg=False, enable_athexapod=False)

    print("*** configure")
    config_data = script.cmd_configure.DataType()
    config_data.config = yaml.safe_dump(config_dict)
    config_id_data = salobj.CommandIdData(1, config_data)
    await script.do_configure(config_id_data)

    print("*** run")
    await script.do_run(None)
    print("*** done")


if __name__ == '__main__':

    asyncio.get_event_loop().run_until_complete(main())
