import asyncio
import logging
import math

import astropy.units as u
from astropy.time import Time
from astropy.coordinates import AltAz, ICRS, EarthLocation, Angle, FK5

from lsst.ts import salobj
from lsst.ts.idl.enums import ATPtg
from ..utils import subtract_angles
import types


class ATTCS:
    """
    High level library for the Auxiliary Telescope Control System

    This is the high level interface for interacting with the CSCs that
    control the Auxiliary Telescope. Essentially this will allow the user to
    slew and track the telescope.

    Parameters
    ----------
    domain: `salobj.Domain`
        Domain to use of the Remotes. If `None`, create a new domain.
    indexed_dome: `bool`
        Compatibility flag for the ATDome. Drop once this is resolved.

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
    """

    def __init__(self, domain=None, indexed_dome=True):

        self.fast_timeout = 5.
        self.long_timeout = 30.
        self.long_long_timeout = 120.
        self.open_dome_shutter_time = 300.

        self.location = EarthLocation.from_geodetic(lon=-70.747698*u.deg,
                                                    lat=-30.244728*u.deg,
                                                    height=2663.0*u.m)

        self._components = ["ATMCS", "ATPtg", "ATAOS", "ATPneumatics",
                            "ATHexapod", "ATDome", "ATDomeTrajectory"]

        self.components = [comp.lower() for comp in self._components]

        self._remotes = {}

        self.domain = domain if domain is not None else salobj.Domain()

        self.check = types.SimpleNamespace()

        for i in range(len(self._components)):
            # FIXME: Drop indexed_dome once this is resolved.
            if indexed_dome and self.components[i] == 'atdome':
                self._remotes[self.components[i]] = salobj.Remote(self.domain,
                                                                  self._components[i],
                                                                  index=1)
            else:
                self._remotes[self.components[i]] = salobj.Remote(self.domain,
                                                                  self._components[i])
            setattr(self.check, self.components[i], True)

        self.start_task = asyncio.gather(*[self._remotes[r].start_task for r in self._remotes])

        self.log = logging.getLogger("ATTCS")

    @property
    def atmcs(self):
        return self._remotes['atmcs']

    @property
    def atptg(self):
        return self._remotes["atptg"]

    @property
    def ataos(self):
        return self._remotes["ataos"]

    @property
    def atpneumatics(self):
        return self._remotes["atpneumatics"]

    @property
    def athexapod(self):
        return self._remotes["athexapod"]

    @property
    def atdome(self):
        return self._remotes["atdome"]

    @property
    def atdometrajectory(self):
        return self._remotes["atdometrajectory"]

    async def slew_icrs(self, ra, dec, rot_sky=None, rot_pa=0.,
                        target_name="slew_icrs", slew_timeout=1200.):
        """Slew the telescope and start tracking an Ra/Dec target in ICRS
        coordinate frame.

        Parameters
        ----------
        ra : `float` or `str`
            Target RA (hour).
        dec : `float` or `str`
            Target Dec (deg).
        rot_sky : `float` or `str`
            Target sky position angle (deg). Default is `None`, which means
            use `rot_pa`.
        rot_pa : `float` or `str`
            Target rotator position angle (deg). Ignored if `rot_sky` is
            given (Default = 0).
        target_name :  `str`
            Target name.
        slew_timeout : `float`
            Timeout for the slew command (second).

        """
        radec_icrs = ICRS(Angle(ra, unit=u.hour),
                          Angle(dec, unit=u.deg))

        rot = None
        if rot_sky is not None:
            raise NotImplementedError("Sky position angle not implemented.")

        else:
            time_data = await self.atptg.tel_timeAndDate.next(flush=True,
                                                              timeout=self.fast_timeout)
            curr_time_atptg = Time(time_data.tai, format="mjd", scale="tai")

            coord_frame_altaz = AltAz(location=self.location, obstime=curr_time_atptg)
            alt_az = radec_icrs.transform_to(coord_frame_altaz)

            rot = 180.-alt_az.alt.deg+Angle(rot_pa, unit=u.deg).deg

        await self.slew(radec_icrs.ra.hour,
                        radec_icrs.dec.deg,
                        rotPA=rot,
                        target_name=target_name,
                        frame=ATPtg.CoordFrame.ICRS,
                        epoch=2000,
                        equinox=2000,
                        parallax=0,
                        pmRA=0,
                        pmDec=0,
                        rv=0,
                        dRA=0,
                        dDec=0,
                        rot_frame=ATPtg.RotFrame.TARGET,
                        rot_mode=ATPtg.RotMode.FIELD,
                        slew_timeout=slew_timeout)

    async def slew(self, ra, dec, rotPA=0., target_name="slew_icrs",
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
            Target Right Ascension (hour)
        dec : float
            Target Declination (degree)
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

    async def startup(self, settings=None):
        """ Startup ATTCS components.

        This method will perform the start of the night procedure for the
        ATTCS component. It will enable all components, open the dome slit,
        and open the telescope covers.

        Parameters
        ----------
        settings: `dict`
            Dictionary with settings to apply.  If `None` use the recommended
            settings.

        Returns
        -------

        """
        self.log.debug("Gathering settings.")
        settings_all = {}
        if settings is not None:
            for s in settings:
                settings_all[s] = settings[s]

        # Give some time for the event loop to run so it can gather the
        # events. Useful for when running on a jupyter notebook, may be
        # removed once we get an `aget` method.
        await asyncio.sleep(1.)
        for comp in self.components:
            if comp not in settings_all:
                sv = getattr(comp, 'evt_settingVersions').get()
                if sv is not None:
                    settings_all[comp] = sv.recommendedSettingsLabels.split(",")[0]
                else:
                    settings_all[comp] = ""

        self.log.debug(f"Settings versions: {settings_all}")

        self.log.debug("Enabling all components")

        set_ss_tasks = []

        for comp in self.components:
            set_ss_tasks.append(salobj.set_summary_state(self._remotes[comp],
                                                         salobj.State.ENABLED,
                                                         settingsToApply=settings_all[comp],
                                                         timeout=self.long_long_timeout))

        ret_val = await asyncio.gather(*set_ss_tasks, return_exceptions=True)

        error_flag = False
        error_msg = ""

        for i in range(len(self.components)):
            if isinstance(ret_val[i], Exception):
                error_flag = True
                error_msg += f"Unable to ENABLE {self.components[i]}\n"
                self.log.error(f"Unable to ENABLE {self.components[i]}")
                self.log.exception(ret_val[i])
            else:
                self.log.debug(f"[{self.components[i]}]::{ret_val[i]!r}")

        if error_flag:
            raise RuntimeError(error_msg)
        else:
            self.log.info("All components enabled.")

        self.log.info("Check that dome CSC can communicate with shutter control box.")

        # FIXME: replace with `aget`.
        scb = self.atdome.evt_scbLink.get()
        if scb is None or not scb.active:
            raise RuntimeError("Dome CSC has no communication with Shutter Control Box. "
                               "Dome controllers may need to be rebooted for connection to "
                               "be established. Cannot continue.")

        self.log.info("Opening dome.")

        self.atdome.evt_shutterInPosition.flush()

        await self.atdome.cmd_moveShutterMainDoor.set_start(open=True,
                                                            timeout=self.long_timeout)

        self.atdome.evt_summaryState.flush()
        # TODO: Monitor self.atdome.tel_position.get().mainDoorOpeningPercentage
        coro_list = [asyncio.ensure_future(self.check_component_state("atdome")),
                     asyncio.ensure_future(self.wait_for_atdome_shutter_inposition())]

        for res in asyncio.as_completed(coro_list):
            try:
                await res
            except RuntimeError as rte:
                await self.cancel_not_done(coro_list)
                raise rte
            else:
                break

        self.log.info("Open telescope cover.")

        await self.atpneumatics.cmd_openM1Cover.start(timeout=self.long_timeout)

        self.log.info("Enable ATAOS corrections.")

        await self.ataos.cmd_enableCorrection.set_start(m1=True,
                                                        timeout=self.long_timeout)

    async def shutdown(self):
        """Shutdown ATTCS components.

        This method will perform the end of the night procedure for the
        ATTCS component. It will close the telescope cover, close the dome,
        move the telescope and dome to the park position and disable all
        components.

        """

        self.log.info("Disabling ATAOS corrections")

        await self.ataos.cmd_disableCorrection.set_start(disableAll=True,
                                                         timeout=self.long_timeout)

        self.log.info("Close telescope cover.")

        await self.atpneumatics.cmd_closeM1Cover.start(timeout=self.long_timeout)

        self.log.info("Disable ATDomeTrajectory")

        await salobj.set_summary_state(self.atdometrajectory,
                                       salobj.State.DISABLED)

        self.log.info("Close dome.")

        self.atdome.evt_shutterInPosition.flush()

        await self.atdome.cmd_closeShutter.set_start(timeout=self.long_timeout)

        self.atdome.evt_summaryState.flush()
        # TODO: Monitor self.atdome.tel_position.get().mainDoorOpeningPercentage
        coro_list = [asyncio.ensure_future(self.check_component_state("atdome")),
                     asyncio.ensure_future(self.wait_for_atdome_shutter_inposition())]

        for res in asyncio.as_completed(coro_list):
            try:
                await res
            except RuntimeError as rte:
                await self.cancel_not_done(coro_list)
                raise rte
            else:
                break

        self.log.info("Put all CSCs in standby")

        set_ss_tasks = []

        for comp in self.components:
            set_ss_tasks.append(salobj.set_summary_state(self._remotes[comp],
                                                         salobj.State.STANDBY,
                                                         timeout=self.long_long_timeout))

        ret_val = await asyncio.gather(*set_ss_tasks, return_exceptions=True)

        error_flag = False
        error_msg = ""

        for i in range(len(self.components)):
            if isinstance(ret_val[i], Exception):
                error_flag = True
                error_msg += f"Unable to put {self.components[i]} in STANDBY\n"
                self.log.error(f"Unable to put {self.components[i]} in STANDBY")
                self.log.exception(ret_val[i])
            else:
                self.log.debug(f"[{self.components[i]}]::{ret_val[i]!r}")

        if error_flag:
            raise RuntimeError(error_msg)
        else:
            self.log.info("All components in standby.")

    async def _slew_to(self, slew_cmd, slew_timeout):
        """Encapsulates "slew" activities.

        Parameters
        ----------
        slew_cmd : `coro`
            One of the slew commands from the atptg remote. Command need to be
            setup before calling this method.

        """
        self.log.debug("Flushing events")
        self.atmcs.evt_allAxesInPosition.flush()

        self.log.debug("Scheduling check coroutines")

        coro_list = [asyncio.ensure_future(self.wait_for_inposition(timeout=slew_timeout)),
                     asyncio.ensure_future(self.monitor_position())]

        for comp in self.components:
            if getattr(self.check, comp):
                getattr(self, comp).evt_summaryState.flush()
                coro_list.append(asyncio.ensure_future(self.check_component_state(comp)))

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

    async def wait_for_inposition(self, timeout):
        """ Wait for both the ATMCS and ATDome to be in position.

        Parameters
        ----------
        timeout: `float`
            How long should it wait before timing out.

        Returns
        -------
        status: `str`
            String with final status.

        """
        status = await asyncio.gather(self.wait_for_atdome_inposition(timeout),
                                      self.wait_for_atmcs_inposition(timeout))

        return f"{status!r}"

    async def wait_for_atmcs_inposition(self, timeout):
        """ Wait for inPosition of atmcs to be ready.

        Parameters
        ----------
        timeout: `float`
            How long should it wait before timing out.

        Returns
        -------
        status: `str`
            String with final status.

        Raises
        ------
        asyncio.TimeoutError
            If does not get a status update in less then `timeout` seconds.

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

    async def wait_for_atdome_inposition(self, timeout):
        """
        Wait for inPosition of atdome to be ready.

        Parameters
        ----------
        timeout: `float`
            How long should it wait before timing out.

        Returns
        -------
        status: `str`
            String with final status.

        Raises
        ------
        asyncio.TimeoutError
            If does not get a status update in less then `timeout` seconds.

        """
        while True:

            in_position = await self.atdome.evt_azimuthInPosition.next(flush=False,
                                                                       timeout=timeout)
            self.log.info(f"Got {in_position.inPosition}")
            if in_position.inPosition:
                self.log.info(f"ATDome in position.")
                return f"ATDome in position."
            else:
                self.log.debug(f"ATDome not in position")

    async def wait_for_atdome_shutter_inposition(self):
        """ Wait for the atdome shutter to be in position.

        Returns
        -------
        status: `str`
            String with final status.

        Raises
        ------
        asyncio.TimeoutError
            If does not get in position before `self.open_dome_shutter_time`

        """

        timeout = self.open_dome_shutter_time

        while True:

            in_position = await self.atdome.evt_shutterInPosition.next(flush=False,
                                                                       timeout=timeout)

            self.log.debug(f"Got: {in_position}")

            if in_position.inPosition:
                self.log.info("ATDome shutter in position.")
                return "ATDome shutter in position."
            else:
                self.log.debug("ATDome shutter not in position.")

    async def monitor_position(self, freq=1.):
        """ Monitor and log the position of the telescope and the dome.

        Parameters
        ----------
        freq: `double`
            Frequency loop should run, in Hz. Default = 1.

        """
        while True:
            comm_pos = await self.atmcs.evt_target.next(flush=True,
                                                        timeout=self.fast_timeout)
            dom_pos = await self.atdome.tel_position.next(flush=True,
                                                          timeout=self.fast_timeout)
            tel_pos = await self.atmcs.tel_mount_AzEl_Encoders.next(flush=True,
                                                                    timeout=self.fast_timeout)

            alt_dif = subtract_angles(comm_pos.elevation, tel_pos.elevationCalculatedAngle[-1])
            az_dif = subtract_angles(comm_pos.azimuth, tel_pos.azimuthCalculatedAngle[-1])
            dom_az_dif = subtract_angles(comm_pos.azimuth, dom_pos.azimuthPosition)

            self.log.info(f"[Telescope] delta Alt = {alt_dif} | delta Az= {az_dif} "
                          f"[Dome] delta Az = {dom_az_dif}")

            await asyncio.sleep(1.)

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

    async def close(self):
        await asyncio.gather(*[self._remotes[r].close() for r in self._remotes])
        await self.domain.close()

    async def __aenter__(self):
        await self.start_task
        return self

    async def __aexit__(self, *args):

        await self.close()
