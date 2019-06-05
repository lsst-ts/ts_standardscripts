import asyncio
import logging
import math
import types

from astropy.time import Time

from lsst.ts import salobj

import SALPY_ATPtg
import SALPY_ATMCS
import SALPY_ATPneumatics
import SALPY_ATHexapod
import SALPY_ATAOS
import SALPY_ATDome
import SALPY_ATDomeTrajectory


class ATTCS:
    """
    High level library for the Auxiliary Telescope Control System

    This is the high level interface for interacting with the CSCs that control the Auxiliary Telescope.
    Essentially this will allow the user to slew and track the telescope.

    Parameters
    ----------
    atmcs: salobj.Remote
    ataos: salobj.Remote
    atpneumatics: salobj.Remote
    athexapod: salobj.Remote
    atdome: salobj.Remote
    atdometrajectory: salobj.Remote
    check: list
        A list of CSC names that will be added to check when performing
        operations.
    within: float
        The relative tolerance of the values to compare.

    Attributes
    ----------
    atmcs: salobj.Remote
    ataos: salobj.Remote
    atpneumatics: salobj.Remote
    athexapod: salobj.Remote
    atdome: salobj.Remote
    atdometrajectory: salobj.Remote
    check: SimpleNamespace
    log: logging.Logger
    within: float
    """

    def __init__(self, atmcs=None, atptg=None, ataos=None, atpneumatics=None, athexapod=None,
                 atdome=None, atdometrajectory=None,
                 check=None, within=0.02):

        self.atmcs = atmcs if atmcs is not None else salobj.Remote(SALPY_ATMCS)
        self.atptg = atptg if atptg is not None else salobj.Remote(SALPY_ATPtg)
        self.ataos = ataos if atptg is not None else salobj.Remote(SALPY_ATAOS)
        self.atpneumatics = atpneumatics if atpneumatics is not None \
            else salobj.Remote(SALPY_ATPneumatics)
        self.athexapod = athexapod if athexapod is not None else salobj.Remote(SALPY_ATHexapod)
        self.atdome = atdome if atdome is not None else salobj.Remote(SALPY_ATDome, 1)
        self.atdometrajectory = atdometrajectory if atdometrajectory is not None \
            else salobj.Remote(SALPY_ATDomeTrajectory)

        csc_namespace = dict()
        for component in self.components():
            if check is not None and component in check:
                csc_namespace[component] = True
            else:
                csc_namespace[component] = False
        self.check = types.SimpleNamespace(**csc_namespace)

        self.log = logging.getLogger("ATTCS")
        self.within = within

    async def slew(self, ra, dec, rotPA=0, target_name="slew_icrs",
                   target_instance=SALPY_ATPtg.ATPtg_shared_TargetInstances_current,
                   frame=SALPY_ATPtg.ATPtg_shared_CoordFrame_icrs,
                   epoch=2000, equinox=2000, parallax=0, pmRA=0, pmDec=0, rv=0, dRA=0, dDec=0,
                   rot_frame=SALPY_ATPtg.ATPtg_shared_RotFrame_target,
                   rot_mode=SALPY_ATPtg.ATPtg_shared_RotMode_field):
        """
        Slew the telescope

        Parameters
        ----------

        ra : float
            desired right ascension to slew to
        dec : float
            desired declination to slew to
        rotPA : float
            desired rotator position angle for slew
        target_name : str
            Name of the target
        target_instance : int
        frame : int
        epoch : float
        equinox : float
        parallax : float
        pmRA : float
        pmDec : float
        rv : float
        dRA : float
        rot_frame : int
        rot_mode : int

        """
        self.atptg.cmd_raDecTarget.set(ra=ra, declination=dec, rotPA=rotPA, targetName=target_name,
                                       targetInstance=target_instance, frame=frame, epoch=epoch,
                                       equinox=equinox, parallax=parallax, pmRA=pmRA, pmDec=pmDec,
                                       rv=rv, dRA=dRA, dDec=dDec, rotFrame=rot_frame,
                                       rotMode=rot_mode)

        self.atmcs.evt_summaryState.flush()
        self.atptg.evt_summaryState.flush()
        self.atmcs.evt_allAxesInPosition.flush()
        self.atptg.cmd_raDecTarget.start(timeout=300)

        coro_list = [asyncio.ensure_future(self.wait_for_position()),
                     asyncio.ensure_future(self.check_atptg_state()),
                     asyncio.ensure_future(self.check_atmcs_state())]

        for res in asyncio.as_completed(coro_list):
            try:
                await res
            except RuntimeError as rte:

                for coro in coro_list:
                    if not coro.done():
                        coro.cancel()
                        try:
                            await coro
                        except asyncio.CancelledError:
                            pass
                raise rte
            else:
                break

    async def check_atmcs_state(self):
        """
        check atmcs state and raise exception if in other state than enabled.
        """
        while True:
            summary_state = await self.atmcs.evt_summaryState.next(flush=False)
            if summary_state.summaryState != salobj.State.ENABLED:
                raise RuntimeError(f"ATMCS state is {salobj.State(summary_state.summaryState)}")

    async def check_csc_heartbeat(self, csc):
        counter = 0
        while counter <= 6:
            heartbeat = await getattr(self, csc).evt_heartbeat.next(flush=False)
            if heartbeat is None:
                counter += 1
            else:
                counter = 0
        raise RuntimeError(f"{csc} not responsive after {counter} heartbeats.")

    async def check_atptg_state(self):
        """
        check atptg state and raise exception if in other state than enabled.
        """
        while True:
            summary_state = await self.atptg.evt_summaryState.next(flush=False)
            if summary_state.summaryState != salobj.State.ENABLED:
                raise RuntimeError(f"ATPtg state is {salobj.State(summary_state.summaryState)}")

    async def check_athexapod_state(self):
        """
        Check athexapod state and raise exeception if in other state than enabled.
        """
        while True:
            summary_state = await self.athexapod.evt_summaryState.next(flush=False)
            if summary_state.summaryState != salobj.State.ENABLED:
                raise RuntimeError(f"ATHexapod state is {salobj.State(summary_state.summaryState)}")

    async def check_atpneumatics_state(self):
        """
        Check atpneumatics state and raise exception if in other state than enabled.
        """
        while True:
            summary_state = await self.atpneumatics.evt_summaryState.next(flush=False)
            if summary_state.summaryState != salobj.State.ENABLED:
                raise RuntimeError(f"ATPneumatics state is {salobj.State(summary_state.summaryState)}")

    async def check_ataos_state(self):
        """
        Check ataos state and raise exception if in other state than enabled.
        """
        while True:
            summary_state = await self.ataos.evt_summaryState.next(flush=False)
            if summary_state.summaryState != salobj.State.ENABLED:
                raise RuntimeError(f"ATAOS state is {salobj.State(summary_state.summaryState)}")

    async def check_atdome_state(self):
        """
        Check atdome state and raise exception if in other state than enabled.
        """
        while True:
            summary_state = await self.atdome.evt_summaryState.next(flush=False)
            if summary_state.summaryState != salobj.State.ENABLED:
                raise RuntimeError(f"ATDome state is {salobj.State(summary_state.summaryState)}")

    async def check_atdometrajectory_state(self):
        """
        Check atdometrajectory state and raise exception if in other state than enabled.
        """
        while True:
            summary_state = await self.atdometrajectory.evt_summaryState.next(flush=False)
            if summary_state.summaryState != salobj.State.ENABLED:
                raise RuntimeError(f"ATDometrajectory state is {salobj.State(summary_state.summaryState)}")

    async def wait_for_position(self):
        """ Wait for position of atmcs to be ready.
        """
        while True:
            in_position = await self.atmcs.evt_allAxesInPosition.next(flush=False)
            self.log.debug(f"Got {in_position.inPosition}")
            if in_position.inPosition:
                self.logo.info(f"Telescope slew finished")
                break

    async def check_tracking(self, track_duration=None):
        """ Check the state of tracking.

        Parameters
        ----------
        track_duration : float
            How long to check for tracking (in seconds). If `None`, will check
            forever.

        """
        start_time = Time.now()
        while Time.now() - start_time < track_duration:
            coro_list = [
                asyncio.ensure_future(self.check_atmcs_state),
                asyncio.ensure_future(self.check_csc_heartbeat("atmcs")),
                asyncio.ensure_future(self.check_atptg_state),
                asyncio.ensure_future(self.check_csc_heartbeat("atptg")),
                asyncio.ensure_future(self.check_target_status)]
            if self.check.atpneumatics:
                coro_list.append(asyncio.ensure_future(self.check_atpneumatics_state))
                coro_list.append(asyncio.ensure_future(self.check_csc_heartbeat("atpneumatics")))
                coro_list.append(asyncio.ensure_future(self.verify_pneumatics))
            if self.check.athexapod:
                coro_list.append(asyncio.ensure_future(self.check_athexapod_state))
                coro_list.append(asyncio.ensure_future(self.check_csc_heartbeat("athexapod")))
                coro_list.append(asyncio.ensure_future(self.verify_hexapod))
            if self.check.atdome:
                coro_list.append(asyncio.ensure_future(self.check_atdome_state))
                coro_list.append(asyncio.ensure_future(self.check_csc_state("atdome")))
            if self.check.atdometrajectory:
                coro_list.append(asyncio.ensure_future(self.check_atdometrajectory))
                coro_list.append(asyncio.ensure_future(self.check_csc_state("atdometrajectory")))
            for res in asyncio.as_completed((coro_list)):
                try:
                    await res
                except RuntimeError as rte:
                    for coro in coro_list:
                        if not coro.done():
                            coro.cancel()
                            try:
                                await coro
                            except asyncio.CancelledError:
                                pass
                    raise rte
                else:
                    break

    async def check_target_status(self):
        """
        Checks the targeting status of the atmcs.
        """
        while True:
            in_position = await self.atmcs.evt_allAxesInPosition.next(flush=False)
            self.log.debug(f"Got {in_position.inPosition}")
            if in_position.inPosition is False:
                raise RuntimeError(f"ATMCS is no longer tracking.")

    async def verify_hexapod(self):
        """
        Verifies that the hexapod commanded values are close to the actual values being returned
        by the hexapod.
        """
        athexapod_inposition = self.athexapod.evt_inPosition.next(flush=True, timeout=60)
        athexapod_positionupdate = self.athexapod.evt_positionUpdate.next(flush=True, timeout=60)
        ataos_hexapod_correction_completed = self.ataos.evt_hexapodCorrectionCompleted.next(
            flush=True,
            timeout=30)
        results = await asyncio.gather(
            athexapod_inposition,
            athexapod_positionupdate,
            ataos_hexapod_correction_completed)
        hexapod_position = results[1]
        hexapod_correction = results[2]
        self.hexapod_check_values(hexapod_position, hexapod_correction, self.within)

    async def verify_pneumatics(self):
        """
        Verifies that the pneumatics mirror pressures are close to the commanded values.
        """
        atpneumatic_m1_set_pressure = self.atpneumatics.evt_m1SetPressure.next(flush=True, timeout=120)
        atpneumatics_m2_set_pressure = self.atpneumatics.evt_m2SetPressure.next(flush=True, timeout=120)
        ataos_m1_correction_started = self.ataos.evt_m1CorrectionStarted.next(flush=True, timeout=120)
        ataos_m2_correction_started = self.ataos.evt_m2CorrectionStarted.next(flush=True, timeout=120)
        results2 = await asyncio.gather(
            ataos_m1_correction_started,
            atpneumatic_m1_set_pressure,
            ataos_m2_correction_started,
            atpneumatics_m2_set_pressure)
        self.pneumatics_check_values(results2[0], results2[1], self.within)
        self.pneumatics_check_values(results2[2], results2[3], self.within)

    def hexapod_check_values(self, athex_position, athex_correction, within):
        """
        Performs the actual check of the hexapod.
        """
        self.log.info(f"Checking hexapod correction within {within*100} percent tolerance")
        c1 = math.isclose(athex_position.positionX, athex_correction.hexapod_x, rel_tol=within)
        self.log.info(
            f"Hexapod x check is {c1}, "
            f"difference is {athex_position.positionX - athex_correction.hexapod_x}")
        c2 = math.isclose(athex_position.positionY, athex_correction.hexapod_y, rel_tol=within)
        self.log.info(
            f"Hexapod y check is {c2}, "
            f"difference is {athex_position.positionY - athex_correction.hexapod_y}")
        c3 = math.isclose(athex_position.positionZ, athex_correction.hexapod_z, rel_tol=within)
        self.log.info(
            f"Hexapod z check is {c3}, "
            f"difference is {athex_position.positionZ - athex_correction.hexapod_z}")
        if (c1 or c2 or c3) is False:
            raise RuntimeError(f"Hexapod not corrected within {within*100} percent tolerance")

    def pneumatics_check_values(self, atpne_pre, atpneu_post, within):
        """
        Performs the actual check of the pneumatics.
        """
        self.log.info(f"checking pneumatics correction within {within*100} percent tolerance")
        c1 = math.isclose(atpne_pre.pressure, atpneu_post.pressure, rel_tol=within)
        self.log.info(f"pneumatics is {c1}, difference is {atpne_pre.pressure - atpneu_post.pressure}")
        if c1 is False:
            raise RuntimeError(f"Pneumatics not corrected within {within*100} percent tolerance")

    async def verify_dome(self):
        atdome_commanded = self.atdome.evt_azimuthCommandedState.next(flush=True, timeout=120)
        atdome_actual = self.atdome.tel_position.next(flush=True)
        atdome_result = await asyncio.gather(atdome_commanded, atdome_actual)
        self.dome_check_values(atdome_result[0], atdome_result[1], within=self.within)

    def dome_check_values(self, atdomecommanded, atdomeactual, within):
        self.log.info(f"checking atdome position within {within*100} percent tolerance")
        c1 = math.isclose(atdomecommanded.azimuth, atdomeactual.azimuthPosition, rel_tol=within)
        self.log.info(f"Dome azimuth is {c1}")
        if c1 is False:
            raise RuntimeError(f"Dome azimuth is not within {within*100} percent tolerance")

    @staticmethod
    def components():
        """Return a list of components names.
        """
        return "ATPtg", "ATMCS", "ATPneumatics", "ATHexapod", "ATAOS", "ATDome", "ATDomeTrajectory"
