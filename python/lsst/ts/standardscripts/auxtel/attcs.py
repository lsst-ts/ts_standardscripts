import asyncio
import logging
import math

from lsst.ts import salobj
from lsst.ts.idl.enums import ATPtg
import types


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
    check: dict
        A dictionary of csc names as the keys with either true or false as the value.
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

    def __init__(self, atmcs, atptg, ataos, atpneumatics, athexapod, atdome, atdometrajectory,
                 check, within=0.02):

        self.components = ["atmcs", "atptg", "ataos", "atpneumatics",
                           "athexapod", "atdome", "atdometrajectory"]

        self.atmcs = atmcs
        self.atptg = atptg
        self.ataos = ataos
        self.atpneumatics = atpneumatics
        self.athexapod = athexapod
        self.atdome = atdome
        self.atdometrajectory = atdometrajectory

        self.check = types.SimpleNamespace(**check)
        self.log = logging.getLogger("ATTCS")
        self.within = within

    async def slew(self, ra, dec, rotPA=0, target_name="slew_icrs",
                   target_instance=ATPtg.TargetInstances.CURRENT,
                   frame=ATPtg.CoordFrame.ICRS,
                   epoch=2000, equinox=2000, parallax=0, pmRA=0, pmDec=0, rv=0, dRA=0, dDec=0,
                   rot_frame=ATPtg.RotFrame.TARGET,
                   rot_mode=ATPtg.RotMode.FIELD,
                   slew_timeout=1200.):
        """
        Slew the telescope and start tracking an Ra/Dec target.

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
        slew_timeout : `float`
            Timeout for the slew command (second).

        """
        self.atptg.cmd_raDecTarget.set(ra=ra, declination=dec, rotPA=rotPA, targetName=target_name,
                                       targetInstance=target_instance, frame=frame, epoch=epoch,
                                       equinox=equinox, parallax=parallax, pmRA=pmRA, pmDec=pmDec,
                                       rv=rv, dRA=dRA, dDec=dDec, rotFrame=rot_frame,
                                       rotMode=rot_mode)

        await self._slew_to(self.atptg.cmd_raDecTarget,
                            slew_timeout=slew_timeout)

    async def slew_to_planet(self, planet, rot_pa=0., slew_timeout=1200.):
        """Slew and track a solar system body.

        Parameters
        ----------
        planet : `ATPtg.Planets`
            Enumeration with planet name.
        rot_pa : `float`
            Desired instrument position angle (degree), Eastwards from North.
        slew_timeout : `float`
            Timeout for the slew command (second).

        """
        self.atptg.cmd_planetTarget.set(planetName=planet.value,
                                        targetInstance=ATPtg.TargetInstances.CURRENT,
                                        dRA=0.,
                                        dDec=0.,
                                        trackId=0,
                                        rotPA=rot_pa)

        await self._slew_to(self.atptg.cmd_planetTarget,
                            slew_timeout=slew_timeout)

    async def check_tracking(self, track_duration=None):
        """Check tracking state. This method monitors all the required
        parameters for tracking a target; from telescope and pointing
        component to the dome.

        If any of those conditions fails, raise an exception.

        This method is useful in case an operation required tracking to be
        active and be interrupted in case tracking stops. One can start
        this method concurrently and monitor it for any exception. If an
        exception is raise, the concurrent task can be interrupted or marked
        as failed as appropriately.

        If a `track_duration` is specified, the method will return after the
        time has passed. Otherwise it will just check forever.

        Parameters
        ----------
        track_duration : `float` or `None`
            How long should tracking be checked for (second)? Must be a
            positive `float` or `None` (default).

        Returns
        -------
        done : `bool`
            True if tracking was successful.

        Raises
        ------
        RuntimeError

            If any of the conditions required for tracking is not met.

        """
        # TODO: properly implement this method

        self.log.debug("Setting up callbacks")

        coro_list = []

        if track_duration is not None and track_duration > 0.:
            coro_list.append(asyncio.ensure_future(asyncio.sleep(track_duration)))

        for cmp in self.components:
            if getattr(self.check, cmp):
                self.log.debug(f"Adding {cmp} to check list")
                coro_list.append(asyncio.ensure_future(self.check_component_state(cmp)))
                # TODO: Implement verify method
                # coro_list.append(asyncio.ensure_future(self.verify(cmp)))
                # TODO: Not all components publish heartbeats!
                # coro_list.append(asyncio.ensure_future(self.check_component_hb(cmp)))
            else:
                self.log.debug(f"Skipping {cmp}")

        for res in asyncio.as_completed(coro_list):
            try:
                await res
            except RuntimeError as rte:
                await self.cancel_not_done(coro_list)
                raise rte
            else:
                break

        await self.cancel_not_done(coro_list)

    async def _slew_to(self, slew_cmd, slew_timeout):
        """Encapsulates "slew" activities.

        Parameters
        ----------
        slew_cmd : `coro`
            One of the slew commands from the atptg remote. Command need to be
            setup before calling this method.

        """
        self.log.debug("Flushing events")
        self.atmcs.evt_summaryState.flush()
        self.atptg.evt_summaryState.flush()
        self.atmcs.evt_allAxesInPosition.flush()

        self.log.debug("Scheduling check coroutines")
        coro_list = [asyncio.ensure_future(self.check_component_state('atptg')),
                     asyncio.ensure_future(self.check_component_state('atmcs')),
                     asyncio.ensure_future(self.wait_for_position(timeout=slew_timeout))]

        self.log.debug("Sending command")
        try:
            await slew_cmd.start(timeout=slew_timeout)
        except Exception as exc:
            await self.cancel_not_done(coro_list)
            raise exc

        self.log.debug("process as completed...")
        for res in asyncio.as_completed(coro_list):
            try:
                ret_val = await res
                self.log.debug(ret_val)
            except RuntimeError as rte:
                self.log.warning("RuntimeError, cancel_not_done.")
                await self.cancel_not_done(coro_list)

                self.log.debug("Removing callback...")
                self.atmcs.evt_summaryState.callback = None
                self.atptg.evt_summaryState.callback = None
                self.atmcs.evt_allAxesInPosition.callback = None

                raise rte
            else:
                break

        await self.cancel_not_done(coro_list)

        self.log.debug("Removing callback...")
        self.atmcs.evt_summaryState.callback = None
        self.atptg.evt_summaryState.callback = None
        self.atmcs.evt_allAxesInPosition.callback = None

    async def check_component_state(self, component):
        """Given a component name wait for an event that specify that the
        state changes. If the event is not ENABLED, raise RuntimeError.

        This is to be used in conjunction with the `get_state_changed_callback`
        method.

        Parameters
        ----------
        component : `str`
            Name of the component to follow. Must be one of:
                atmcs, atptg, ataos, atpneumatics, athexapod, atdome,
                atdometrajectory

        Raises
        ------
        RuntimeError

            if state is not ENABLED.

        """

        while True:

            _state = await getattr(self, f"{component}").evt_summaryState.next(flush=False)

            state = salobj.State(_state.summaryState)

            if state != salobj.State.ENABLED:
                self.log.warning(f"{component} not enabled: {state!r}")
                raise RuntimeError(f"{component} state is {state!r}")
            else:
                self.log.debug(f"{component}: {state!r}")

    async def check_csc_heartbeat(self, csc):
        counter = 0
        while counter <= 6:
            heartbeat = await getattr(self, csc).evt_heartbeat.next(flush=False)
            if heartbeat is None:
                counter += 1
            else:
                counter = 0
        raise RuntimeError(f"{csc} not responsive after {counter} heartbeats.")

    async def wait_for_position(self, timeout):
        """
        Wait for position of atmcs to be ready.
        """
        while True:

            in_position = await self.atmcs.evt_allAxesInPosition.next(flush=False,
                                                                      timeout=timeout)
            self.log.info(f"Got {in_position.inPosition}")
            if in_position.inPosition:
                self.log.info(f"Telescope in position.")
                return f"Telescope in position."
            else:
                self.log.debug(f"Telescope not in position")

    async def check_target_status(self):
        """
        Checks the targeting status of the atmcs.
        """
        while True:
            in_position = await self.atmcs.evt_allAxesInPosition.next(flush=False)
            self.log.debug(f"Got {in_position.inPosition}")
            if in_position.inPosition is False:
                raise RuntimeError(f"ATMCS is no longer tracking.")

    async def verify(self, component):
        """

        Parameters
        ----------
        component

        Returns
        -------

        """
        raise NotImplementedError("Method needs to be implemented.")

    async def verify_hexapod(self):
        """
        Verifies that the hexapod commanded values are close to the actual values being returned
        by the hexapod.
        """
        # FIXME: This method needs to be fixed so not to use `next` on events
        # because it is not possible to properly cancel them.
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
    async def cancel_not_done(coro_list):
        """Appropriately cancel all coroutines in `coro_list`.

        Parameters
        ----------
        coro_list : `list(coroutines)`
            A list of coroutines to cancel.

        """

        for coro in coro_list:
            if not coro.done():
                coro.cancel()
                try:
                    await coro
                except asyncio.CancelledError:
                    pass
