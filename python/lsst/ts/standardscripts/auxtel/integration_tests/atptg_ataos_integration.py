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

from lsst.ts import salobj
from lsst.ts import scriptqueue

import SALPY_ATAOS
import SALPY_ATPtg
import SALPY_ATMCS


class ATPtgATAOSIntegration(scriptqueue.BaseScript):
    """Test integration between the ATPtg and ATAOS CSCs.

    Parameters
    ----------
    index : `int`
        Index of Script SAL component.
    """
    __test__ = False  # stop pytest from warning that this is not a test

    def __init__(self, index):
        super().__init__(index=index,
                         descr="Test integration between ATPtg and ATAOS",
                         remotes_dict=dict(ataos=salobj.Remote(SALPY_ATAOS),
                                           atptg=salobj.Remote(SALPY_ATPtg),
                                           atmcs=salobj.Remote(SALPY_ATMCS)))
        self.location = EarthLocation.from_geodetic(lon=-70.747698*u.deg,
                                                    lat=-30.244728*u.deg,
                                                    height=2663.0*u.m)

        self.el = None
        self.az = None
        self.enable_ataos = False
        self.enable_atptg = False
        self.enable_atmcs = False

        self.timeout = 30.  # general timeout in seconds.

    async def configure(self, el=30, az=0,
                        enable_ataos=True, enable_atptg=True,enable_atmcs=True):
        """Configure the script.

        Parameters
        ----------
        el : `float`
            Approximate elevation of target (deg).
        az : `float`
            Approximate azimuth of target (deg).
        enable_ataos : `bool` (optional)
            Enable the ATAOS CSC?
        enable_atptg : `bool` (optional)
            Enable the ATPtg CSC?
        """
        self.el = float(el)*u.deg
        self.az = float(az)*u.deg
        self.enable_ataos = bool(enable_ataos)
        self.enable_atptg = bool(enable_atptg)
        self.enable_atmcs = bool(enable_atmcs)

    def assertEqual(self, what, val1, val2, more=""):
        if val1 != val2:
            raise RuntimeError(f"{what} = {val1}; should be {val2} {more}")

    async def run(self):
        # Enable ATAOS and ATPgt, if requested, else check they are enabled
        await self.checkpoint("enable_cscs")
        if self.enable_ataos:
            self.log.info(f"Enable ATAOS")
            try:
                await self.ataos.cmd_start.start()
            except Exception as e:
                self.log.exception(e)

            try:
                await self.ataos.cmd_enable.start()
            except Exception as e:
                self.log.exception(e)
        else:
            data = self.ataos.evt_summaryState.get()
            self.assertEqual("ATAOS summaryState",
                             salobj.State(data.summaryState),
                             salobj.State.ENABLED, "ENABLED")

        if self.enable_atptg:
            self.log.info("Enable ATPtg")
            try:
                await self.atptg.cmd_start.start()
            except Exception as e:
                self.log.exception(e)

            try:
                await self.atptg.cmd_enable.start()
            except Exception as e:
                self.log.exception(e)
        else:
            data = self.atptg.evt_summaryState.get()
            self.assertEqual("ATPtg summaryState",
                             data.summaryState, salobj.State.ENABLED, "ENABLED")
        if self.enable_atmcs:
            self.log.info("Enable ATMCS")
            try:
                await self.atmcs.cmd_start.start()
            except Exception as e:
                self.log.exception(e)
            try:
                await self.atmcs.cmd_enable.start()
            except Exception as e:
                self.log.exception(e)
        else:
            data = self.atmcs.evt_summaryState.get()
            self.assertEqual(
                    "ATMCS summaryState",
                    data.summaryState,
                    salobj.State.ENABLED,
                    "ENABLED"
                    )

        await self.checkpoint("start_tracking")
        # Docker containers can have serious clock drift,
        # so just the time reported by ATPtg
        time_data = await self.atptg.tel_timeAndDate.next(flush=False, timeout=self.timeout)
        curr_time_atptg = Time(time_data.tai, format="mjd", scale="tai")
        time_err = curr_time_atptg - Time.now()
        self.log.info(f"Time error={time_err.sec:0.2f} sec")

        # Compute RA/Dec for commanded az/el
        cmd_elaz = AltAz(alt=self.el, az=self.az, obstime=curr_time_atptg.tai, location=self.location)
        cmd_radec = cmd_elaz.transform_to(ICRS)

        # Start tracking
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

        ack_id = await self.atptg.cmd_raDecTarget.start(timeout=self.timeout)
        self.assertEqual("raDecTarget command result",
                         ack_id.ack.error, 0)
        self.log.info(f"raDecTarget command result: {ack_id.ack.result}")

        # make sure at least one current Target status was published...
        self.log.debug("Waiting for currentTargetStatus to be published.")
        target_status = await self.atmcs.evt_target.next(
                flush=True,
                timeout=self.timeout)
        self.log.debug(f"Got {target_status.demandRaString} {target_status.demandDecString}.")

        await self.checkpoint("apply_correction_manually")

        self.ataos.cmd_disableCorrection.set(disableAll=True)
        ack_id = await self.ataos.cmd_disableCorrection.start(timeout=self.timeout)
        self.log.info(f"disableCorrections command result: {ack_id.ack.result}")

        ack_id = await self.ataos.cmd_applyCorrection.start(timeout=self.timeout)
        self.log.info(f"applyCorrection command result: {ack_id.ack.result}")

        await self.checkpoint("enable_all_corrections")
        # Enable all corrections for ATAOS
        self.ataos.cmd_enableCorrection.set(enableAll=True)
        ack_id = await self.ataos.cmd_enableCorrection.start(timeout=self.timeout)
        self.log.info(f"enableCorrections command result: {ack_id.ack.result}")

        # Wait until ATAOS publishes that corrections were performed
        hexapod_completed = self.ataos.evt_hexapodCorrectionCompleted.next(flush=True,
                                                                           timeout=self.timeout)
        m1_completed = self.ataos.evt_m1CorrectionCompleted.next(flush=True,
                                                                 timeout=self.timeout)
        m2_completed = self.ataos.evt_m2CorrectionCompleted.next(flush=True,
                                                                 timeout=self.timeout)

        await asyncio.gather(hexapod_completed,
                             m1_completed,
                             m2_completed)

    def set_metadata(self, metadata):
        metadata.duration = 60  # rough estimate

    async def cleanup(self):
        # Stop tracking
        self.log.info("cleanup")
        try:
            await self.atptg.cmd_disable.start(timeout=1)
        except salobj.AckError as e:
            self.log.error(f"ATPtg disable failed with {e}")
        else:
            self.log.info("Disabled ATPtg")

        try:
            await self.atptg.cmd_standby.start(timeout=1)
        except salobj.AckError as e:
            self.log.error(f"ATPtg disable failed with {e}")
        else:
            self.log.info("ATPtg standby")

        try:
            await self.ataos.cmd_disable.start(timeout=1)
        except salobj.AckError as e:
            self.log.error(f"ATAOS disable failed with {e}")
        else:
            self.log.info("Disabled ATAOS")

        try:
            await self.ataos.cmd_standby.start(timeout=1)
        except salobj.AckError as e:
            self.log.error(f"ATAOS disable failed with {e}")
        else:
            self.log.info("ATAOS standby")

        try:
            await self.atmcs.cmd_disable.start(timeout=5)
        except salobj.AckError as e:
            self.log.error(f"ATMCS disable failed with {e}")
        else:
            self.log.info("ATMCS Disabled")

        try:
            await self.atmcs.cmd_standby.start(timeout=5)
        except salobj.AckError as e:
            self.log.error(f"ATMCS standby failed with {e}")
        else:
            self.log.info("ATMCS standby")


async def main(index):
    import logging

    print("*** initializing script")
    script = ATPtgATAOSIntegration(index=index)
    script.log.setLevel(logging.DEBUG)
    script.log.addHandler(logging.StreamHandler())
    script.ataos.cmd_setLogLevel.set(level=logging.DEBUG)
    await script.ataos.cmd_setLogLevel.start()
    print("*** configure")
    config_data = script.cmd_configure.DataType()
    config_data.config = ""
    config_id_data = salobj.CommandIdData(1, config_data)
    await script.do_configure(config_id_data)
    print("*** run")
    await script.do_run(None)
    print("*** done")


if __name__ == "__main__":
    asyncio.get_event_loop().run_until_complete(main(index=1))
