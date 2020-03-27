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

__all__ = ["ATTracking"]

import yaml
import asyncio
import logging
import types

import astropy.units as u
from astropy.time import Time
from astropy.coordinates import AltAz, ICRS, EarthLocation

from lsst.ts import salobj
from lsst.ts import scriptqueue
from lsst.ts.standardscripts.auxtel.attcs import ATTCS
from lsst.ts.idl.enums import ATPtg


class ATTracking(scriptqueue.BaseScript):
    """Test integration between the ATPtg and ATMCS CSCs.

    Parameters
    ----------
    index : `int`
        Index of Script SAL component.
    """

    __test__ = False  # stop pytest from warning that this is not a test

    def __init__(self, index):
        super().__init__(index=index, descr="Test integration between ATPtg and ATMCS")
        self.atmcs = salobj.Remote(self.domain, name="ATMCS")
        self.atptg = salobj.Remote(self.domain, name="ATPtg")
        self.ataos = salobj.Remote(self.domain, name="ATAOS")
        self.athexapod = salobj.Remote(self.domain, name="ATHexapod")
        self.atpneumatics = salobj.Remote(self.domain, name="ATPneumatics")
        self.atdome = salobj.Remote(self.domain, name="ATDome")
        self.atdometrajectory = salobj.Remote(self.domain, name="ATDomeTrajectory")
        self.location = EarthLocation.from_geodetic(
            lon=-70.747698 * u.deg, lat=-30.244728 * u.deg, height=2663.0 * u.m
        )
        self.attcs = ATTCS(
            atmcs=self.atmcs,
            atptg=self.atptg,
            ataos=self.ataos,
            athexapod=self.athexapod,
            atpneumatics=self.atpneumatics,
            atdome=self.atdome,
            atdometrajectory=self.atdometrajectory,
        )
        self.in_fault = False

        self.pool_time = 10.0  # wait time in tracking test loop (seconds)

    @classmethod
    def get_schema(cls):
        schema = """
        $schema: http://json-schema.org/draft-07/schema#
        $id: https://github.com/lsst-ts/ts_standardscripts/auxtel/ATTrackingATTCS.yaml
        title: ATTrackingATTCS v1
        description: configuration for ATTracking ATTCS.
        type: object
        properties:
            el:
                description: Approximate elevation of target (deg).
                type: number
                default: 45.0
            az:
                description: Approximate azimuth of target (deg).
                type: number
                default: 45.0
            max_sep:
                description: Maximum allowed on-sky separation between expected az/alt
                and the target az/alt computer by the ATPtg (deg).
                This need not be tiny; it is meant to be a sanity check.
                type: number
                default: 1.0
            track_duration:
                description: How long to track after slewing to position (hour).
                type: number
                default: 0.02
            max_track_error:
                description: Maximum allowed on-sky separation between commanded and
                measured az/el (arcsec).
                type: number
                default: 0.05
            enable_atmcs:
                description: Enable the atmcs.
                type: boolean
                default: True
            enable_atptg:
                description: Enable the atptg.
                type: boolean
                default: True
            enable_ataos:
                description: Enable the ataos.
                type: boolean
                default: True
            enable_athexapod:
                description: Enable the athexapod.
                type: boolean
                default: True
            enable_atpneumatics:
                description: Enable the atpneumatics.
                type: boolean
                default: True
            within:
                description: How close in percentage, actual values are to commanded values.
                type: number
                default: True
            check:
                description: A dictionary of values to check the status of certain CSCs.
                type: object
                properties:
                    athexapod:
                        description: boolean that checks the athexapod or does not.
                        type: boolean
                        default: True
                    atpneumatics:
                        description: boolean that checks the atpneumatics or does not.
                        type: boolean
                        default: True
                    atdome:
                        description: boolean that checks the atdome or does not.
                        type: boolean
                        default: True
                    atdometrajectory:
                        description: boolean that checks the atdometrajectory or does not.
                        type: boolean
                        default: True
        additionalProperties: False
        """
        return yaml.safe_dump(schema)

    async def configure(self, config):
        """Configure the script.

        Parameters
        ----------
        config : `types.SimpleNamespace`
            Script configuration.
        """
        self.el = float(self.config.el) * u.deg
        self.az = float(self.config.az) * u.deg
        self.max_sep = float(self.config.max_sep) * u.deg
        self.track_duration = float(self.config.track_duration) * u.hour
        self.max_track_error = float(self.config.max_track_error) * u.arcsec
        self.enable_atmcs = bool(self.config.enable_atmcs)
        self.enable_atptg = bool(self.config.enable_atptg)
        self.enable_ataos = bool(self.config.enable_ataos)
        self.enable_athexapod = bool(self.config.enable_athexapod)
        self.enable_atpneumatics = bool(self.config.enable_atpneumatics)
        self.within = float(self.config.within)
        self.attcs.within = self.within
        self.attcs.check = types.SimpleNamespace(**self.config.check)

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
            data = await self.atmcs.evt_summaryState.next(flush=False)
            self.assertEqual(
                "ATMCS summaryState", data.summaryState, salobj.State.ENABLED, "ENABLED"
            )
        if self.enable_atptg:
            self.log.info("Enable ATPtg")
            await salobj.enable_csc(self.atptg)
        else:
            data = await self.atptg.evt_summaryState.next(flush=False)
            self.assertEqual(
                "ATPtg summaryState", data.summaryState, salobj.State.ENABLED, "ENABLED"
            )
        if self.enable_ataos:
            self.log.info("Enable ATAOS")
            await salobj.enable_csc(self.ataos, settingsToApply="test")
        else:
            data = await self.ataos.evt_summaryState.next(flush=False)
            self.assertEqual(
                "ATAOS summaryState", data.summaryState, salobj.State.ENABLED, "ENABLED"
            )
        if self.enable_athexapod:
            self.log.info("Enable ATHexapod")
            await salobj.enable_csc(self.athexapod)
        else:
            data = await self.athexapod.evt_summaryState.next(flush=False, timeout=10)
            self.assertEqual(
                "ATHexapod summaryState",
                data.summaryState,
                salobj.State.ENABLED,
                "ENABLED",
            )
        if self.enable_atpneumatics:
            self.log.info("Enable ATPneumatics")
            await salobj.enable_csc(self.atpneumatics)
        else:
            data = await self.atpneumatics.evt_summaryState.next(
                flush=False, timeout=10
            )
            self.assertEqual(
                "ATPneumatics summaryState",
                data.summaryState,
                salobj.State.ENABLED,
                "ENABLED",
            )
        if self.enable_atdome:
            self.log.info("Enable ATDome")
            await salobj.enable_csc(self.atdome)
        else:
            data = await self.atdome.evt_summaryState.next(flush=False, timeout=10)
            self.assertEqual(
                "ATDome summaryState",
                data.summaryState,
                salobj.State.ENABLED,
                "ENABLED",
            )
        if self.enable_atdometrajectory:
            self.log.info("Enable ATDometrajectory")
            await salobj.enable_csc(self.atdometrajectory)
        else:
            data = await self.atdometrajectory.evt_summaryState.next(
                flush=False, timeout=10
            )
            self.assertEqual(
                "ATDome summaryState",
                data.summaryState,
                salobj.State.ENABLED,
                "ENABLED",
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
            alt=self.el, az=self.az, obstime=curr_time_atptg.tai, location=self.location
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
        self.ataos.cmd_enableCorrection.set(enableAll=True)
        await self.ataos.cmd_enableCorrection.start(timeout=10)
        ack_id = await self.atptg.cmd_raDecTarget.start(timeout=2)
        self.log.info(f"raDecTarget command result: {ack_id.ack.result}")

        # Check the target el/az
        # Use time from the target event, since that is the time at which
        # the position was specified.
        data = await self.atmcs.evt_target.next(flush=True, timeout=1)
        # TODO DM-24051: ditch this hack when we no longer need ts_xml 4.8
        if hasattr(data, "taiTime"):
            event_tai = data.taiTime
        else:
            event_tai = data.time
        target_time = Time(event_tai, scale="tai", format="unix")
        curr_time_local = Time.now()
        dtime = event_tai - curr_time_local.tai.unix
        self.log.info(
            f"target event time={event_tai:0.2f}; "
            f"current tai unix ={curr_time_local.tai.unix:0.2f}; "
            f"diff={dtime:0.2f} sec"
        )
        self.log.info(
            f"desired el={self.el.value:0.2f}, az={self.az.value:0.2f}; "
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
        self.log.info(f"el/az separation={separation}; max={self.max_sep}")
        if separation > self.max_sep:
            raise RuntimeError(f"az/el separation={separation} > {self.max_sep}")

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

        if self.track_duration == 0.0:
            self.log.info("Skipping track test...")
            return

        self.log.info(
            f"Monitoring tracking for {self.track_duration}. Wait for "
            f"allAxesInPosition event."
        )
        while True:
            in_position = await self.atmcs.evt_allAxesInPosition.next(
                flush=False, timeout=20
            )
            self.log.debug(f"Got {in_position.inPosition}")
            if in_position.inPosition:
                break

        await self.attcs.check_track(track_duration=self.track_duration)

    def set_metadata(self, metadata):
        metadata.duration = 60  # rough estimate

    async def cleanup(self):
        # Stop tracking
        self.log.info("cleanup")
        try:
            await self.atptg.cmd_stopTracking.start(timeout=1)
            # disable corrections
            self.ataos.cmd_disableCorrections.set(disableAll=True)
            await self.ataos.cmd_disableCorrections.start(timeout=5)
        except salobj.AckError as e:
            self.log.error(f"ATPtg stopTracking failed with {e}")
        else:
            self.log.info("Tracking stopped")


async def main():

    script = ATTracking(index=10)

    script.log.setLevel(logging.INFO)
    script.log.addHandler(logging.StreamHandler())

    config_dict = dict(
        enable_atmcs=True,
        enable_atptg=False,
        enable_athexapod=False,
        enable_atpneumatics=False,
        track_duration=0.06,
        within=0.02,
    )

    print("*** configure")
    config_data = script.cmd_configure.DataType()
    config_data.config = yaml.safe_dump(config_dict)
    config_id_data = salobj.CommandIdData(1, config_data)
    await script.do_configure(config_id_data)

    print("*** run")
    await script.do_run(None)
    print("*** done")


if __name__ == "__main__":

    asyncio.get_event_loop().run_until_complete(main())
