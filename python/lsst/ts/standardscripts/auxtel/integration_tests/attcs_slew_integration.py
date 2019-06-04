from lsst.ts.standardscripts.auxtel.attcs import ATTCS
from lsst.ts import salobj
from lsst.ts import scriptqueue

import asyncio
import yaml
import logging

import astropy.units as u
from astropy.coordinates import AltAz, ICRS, EarthLocation
from astropy.time import Time

import SALPY_ATMCS
import SALPY_ATPtg
import SALPY_ATAOS
import SALPY_ATHexapod
import SALPY_ATPneumatics
import SALPY_ATDome
import SALPY_ATDomeTrajectory


class ATTCSSlewIntegration(scriptqueue.BaseScript):

    def __init__(self, index):

        atMcsRem = salobj.Remote(SALPY_ATMCS)
        atPtgRem = salobj.Remote(SALPY_ATPtg)
        atAosRem = salobj.Remote(SALPY_ATAOS)
        atPneuRem = salobj.Remote(SALPY_ATPneumatics)
        atHexRem = salobj.Remote(SALPY_ATHexapod)
        atDomeRem = salobj.Remote(SALPY_ATDome)
        atDomeTrajRem = salobj.Remote(SALPY_ATDomeTrajectory)

        super().__init__(index=index,
                         descr="integration test for components involved in slewing operations",
                         remotes_dict=dict(atmcs=atMcsRem,
                                           atptg=atPtgRem,
                                           ataos=atAosRem,
                                           athexapod=atHexRem,
                                           atpneumatics=atPneuRem,
                                           atdome=atDomeRem,
                                           atdometrajectory=atDomeTrajRem))
        self.location = EarthLocation.from_geodetic(lon=-70.747698*u.deg,
                                                    lat=-30.244728*u.deg,
                                                    height=2663.0*u.m)

        self.attcs = ATTCS(atMcsRem, atPtgRem, atAosRem, 
                           atPneuRem, atHexRem, atDomeRem,
                           atHexRem)

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
                        enable_atpneumatics=True,
                        enable_atdome=True,
                        enable_atdometrajectory=True):
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
        self.enable_atdome = bool(enable_atdome)
        self.enable_atdometrajectory = bool(enable_atdometrajectory)

    async def run(self):
        # Enable components if requested, else check they are enabled
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
        if self.enable_atdome:
            self.log.info("Enable ATDome")
            await salobj.enable_csc(self.atdome)
        else:
            data = await self.atdome.evt_summaryState.next(flush=False, timeout=self.timeout)
            self.assertEqual("ATDome summaryState",
                             data.summaryState,
                             salobj.State.ENABLED,
                             "ENABLED")
        if self.enable_atdomeTrajectory:
            self.log.info("Enable ATDomeTrajectory")
            await salobj.enable_csc(self.atdometrajectory)
        else:
            data = await self.atdometrajectory.evt_summaryState.next(flush=False, timeout=self.timeout)
            self.assertEqual("ATDomeTrajectory summaryState",
                             data.summaryState,
                             salobj.State.ENABLED,
                             "ENABLED")

        # Docker containers can have serious clock drift,
        # so just the time reported by ATPtg
        time_data = await self.atptg.tel_timeAndDate.next(flush=False, timeout=2)
        curr_time_atptg = Time(time_data.tai, format="mjd", scale="tai")
        time_err = curr_time_atptg - Time.now()
        self.log.info(f"Time error={time_err.sec:0.2f} sec")

        # Compute RA/Dec for starting az/el
        startelaz = AltAz(alt=self.startEl, az=self.startAz, obstime=curr_time_atptg.tai,
                          location=self.location)
        startradec = startelaz.transform_to(ICRS)

        # Compute RA/Dec for ending az/el
        endelaz = AltAz(alt=self.endEl, az=self.endAz, obstime=curr_time_atptg.tai,
                        location=self.location)
        endradec = endelaz.transform_to(ICRS)

        await self.attcs.slew(startradec.ra.hour, startradec.dec.deg)
        await self.attcs.slew(endradec.ra.hour, endradec.dec.deg)

    async def main():

        script = ATTCSSlewIntegration(index=8)

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