# This file is part of ts_standardscripts
#
# Developed for the LSST Telescope and Site Systems.
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

__all__ = ["DomeTrajectoryMCS"]

import asyncio
import math
import yaml

from lsst.ts import salobj
from lsst.ts.idl.enums.ATDome import AzimuthCommandedState, AzimuthState

STD_TIMEOUT = 5  # timeout for normal commands (sec)
SLEW_TIMEOUT = 60  # maximum time for dome and telescope to slew (sec)
TRACK_INTERVAL = 0.5  # interval between tracking updates (sec)

RAD_PER_DEG = math.pi / 180


class DomeTrajectoryMCS(salobj.BaseScript):
    """Test integration between the ATDomeTrajectory, ATDome and ATMCS CSCs.

    Parameters
    ----------
    index : `int`
        Index of Script SAL component.
    """

    __test__ = False  # stop pytest from warning that this is not a test

    def __init__(self, index):
        super().__init__(index=index, descr="Test integration between ATDome and ATMCS")
        self.atmcs = salobj.Remote(
            domain=self.domain,
            name="ATMCS",
            include=[
                "summaryState",
                "track",
                "target",
                "elevationInPosition",
                "azimuthInPosition",
                "mount_AzEl_Encoders",
                "measuredMotorVelocity",
            ],
        )
        self.atdometraj = salobj.Remote(domain=self.domain, name="ATDomeTrajectory")
        self.atdome = salobj.Remote(domain=self.domain, name="ATDome")
        self._track_task = None
        self.track_elaz = None

    @classmethod
    def get_schema(cls):
        schema_yaml = """
            $schema: http://json-schema.org/draft-07/schema#
            $id: https://github.com/lsst-ts/ts_standardscripts/auxtel/SlewTelescopeIcrs.yaml
            title: SlewTelescopeIcrs v1
            description: Configuration for SlewTelescopeIcrs
            type: object
            properties:
              el:
                description: Desired telescope elevation (deg)
                type: number
                default: 30
              azmin:
                description: Minimum commanded telescope azimuth (deg)
                type: number
                exclusiveMaximum: 0
                default: -270
              azmax:
                description: Maximum commanded telescope azimuth (deg)
                type: number
                exclusiveMinimum: 0
                default: 270
            required: [el, azmin, azmax]
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
        self.config = config

    async def run(self):
        """Run the script.

        The basic sequence is:
        - Set things up
        - Slew the telescope to the configured elevation and dome azimuth
        - Check that the dome did not move
        - Slew the telescope by less than the dome tolerance
        - Check that the dome did not move
        - Slew the telescope by more than the dome tolerance / cos(el)
        - Check that the dome did move
        """
        self.log.info("Disable ATDomeTrajectory")
        await salobj.set_summary_state(self.atdometraj, salobj.State.DISABLED)

        self.log.info("Enable ATDome and stop motion")
        await salobj.set_summary_state(self.atdome, salobj.State.ENABLED)

        self.atdome.evt_azimuthCommandedState.flush()
        await self.atdome.cmd_stopMotion.start(timeout=STD_TIMEOUT)
        dome_az_cmd_state = await self.atdome.evt_azimuthCommandedState.next(
            flush=False, timeout=STD_TIMEOUT
        )
        assert (
            dome_az_cmd_state.commandedState == AzimuthCommandedState.STOP
        ), f"ATDome commanded state={dome_az_cmd_state.commandedState} != Stop={AzimuthCommandedState.STOP}"

        # Enable ATMCS and stop tracking
        self.log.info("Enable ATMCS and stop tracking")
        await salobj.set_summary_state(self.atmcs, salobj.State.ENABLED)
        await self.atmcs.cmd_stopTracking.start(timeout=STD_TIMEOUT)

        # Get ATDomeTrajectory max_az configuration parameter:
        # telescope/dome az differences smaller than this
        # result in no dome rotation, but likely this will be scaled
        # by cos(el) someday, so compute that scaled value as well
        # TODO: improve this when we have configuration standardized;
        # right now there is no way to get this value from ATDomeTrajectory
        atdometraj_max_az = 5
        scaled_atdometraj_max_az = atdometraj_max_az / math.cos(
            self.config.el * RAD_PER_DEG
        )
        self.log.info(
            f"ATDomeTrajectory max_az={atdometraj_max_az:0.2f}; "
            f"scaled by cos(alt)={scaled_atdometraj_max_az:0.2f}"
        )

        # Wait until the mount stops slewing
        self.log.info("Wait for the telescope mount to stop")
        max_vel = 0.001  # deg/sec
        while True:
            mount_vel = await self.atmcs.tel_measuredMotorVelocity.next(
                flush=False, timeout=STD_TIMEOUT
            )
            if (
                abs(mount_vel.elevationMotorVelocity[-1]) < max_vel
                and abs(mount_vel.azimuthMotor1Velocity[-1]) < max_vel
                and abs(mount_vel.azimuthMotor2Velocity[-1]) < max_vel
            ):
                break

        # Report current el/az
        curr_elaz = await self.atmcs.tel_mount_AzEl_Encoders.next(
            flush=False, timeout=STD_TIMEOUT
        )
        self.log.info(
            f"telescope initial el={curr_elaz.elevationCalculatedAngle[-1]:0.2f}, "
            f"az={curr_elaz.azimuthCalculatedAngle[-1]:0.2f}"
        )

        # Wait for the dome to stop
        self.log.info("Wait for the dome to stop")
        az_state = self.atdome.evt_azimuthState.get()
        while az_state.state != AzimuthState.NOTINMOTION:
            az_state = await self.atdome.evt_azimuthState.next(
                flush=False, timeout=SLEW_TIMEOUT
            )
        dome_pos = await self.atdome.tel_position.next(flush=True, timeout=STD_TIMEOUT)
        dome_az = dome_pos.azimuthPosition
        self.log.info(f"dome az={dome_az:0.2f}")

        # Compute nearest telescope azimuth to dome
        # dome azimuth is in range [0, 360]
        # and telescope azimuth limits straddle 0
        az_choices = []
        for az_choice in dome_az - 360, dome_az:
            if self.config.azmin < az_choice < self.config.azmax:
                az_choices.append(az_choice)
        new_tel_az = az_choices[0]
        if len(az_choices) == 0:
            raise RuntimeError(
                "No suitable azimuth found; az limits too close together"
            )
        elif len(az_choices) == 2:
            daz = abs(curr_elaz[1] - new_tel_az)
            if abs(curr_elaz[1] - az_choices[1]) < daz:
                new_tel_az = az_choices[1]

        # Slew telescope to dome position;
        # move the telescope instead of the dome for several reasons:
        # * I want the telescope at the specified elevation
        # * the dome has a dead band and I want accurate alignment
        # * the telescope is faster than the dome
        self.track_telescope(el=self.config.el, az=new_tel_az)
        self.log.info(
            f"Slewing telescope to elevation={self.config.el:0.2f}, "
            f"azimuth={new_tel_az:0.2f}: match dome azimuth"
        )

        def show_tel_elaz(data):
            self.log.debug(
                f"Current telescope el={data.elevationCalculatedAngle[-1]:0.2f}, "
                f"az={data.azimuthCalculatedAngle[-1]:0.2f}"
            )

        self.atmcs.tel_mount_AzEl_Encoders.callback = show_tel_elaz

        # wait for next target event
        target = await self.atmcs.evt_target.next(flush=True, timeout=STD_TIMEOUT)
        # sanity-check the target
        assert abs(target.elevation - self.track_elaz[0]) < 0.01
        # telescope azimuth is absolute (not wrapped), so simply subtract
        assert abs(target.azimuth - self.track_elaz[1]) < 0.01

        # Enable ATDomeTrajectory
        # This commands a move because the commanded dome azimuth is unknown
        # (due to being stopped), but it should be to the telescope azimuth
        self.log.info("Enable ATDomeTrajectory")
        await self.atdometraj.cmd_enable.start(timeout=STD_TIMEOUT)

        # Commanded dome azimuth should match target azimuth
        dome_pos = await self.atdome.tel_position.next(flush=True, timeout=STD_TIMEOUT)
        dome_az_cmd_state = await self.atdome.evt_azimuthCommandedState.next(
            flush=False, timeout=STD_TIMEOUT
        )
        self.log.info(
            f"As telescope slew starts: "
            f"dome commanded state={dome_az_cmd_state.commandedState}; "
            f"commanded azimuth={dome_az_cmd_state.azimuth:0.2f}; "
            f"current azimuth={dome_pos.azimuthPosition:0.2f}"
        )
        assert dome_az_cmd_state.commandedState == AzimuthCommandedState.GOTOPOSITION, (
            f"ATDome azimuth commanded state={dome_az_cmd_state.commandedState} != "
            f"GoToPosition={AzimuthCommandedState.GOTOPOSITION}"
        )
        assert (
            abs(salobj.angle_diff(dome_pos.azimuthPosition, self.track_elaz[1]).deg)
            <= 0.1
        ), (
            f"Dome current azimuth={dome_pos.azimuthPosition:0.2f} != "
            f"{self.track_elaz[1]:0.2f} = telescope target azimuth"
        )

        # Wait for elevation and azimuth; ignore rotators and M3
        data = self.atmcs.evt_elevationInPosition.get()
        if not data.inPosition:
            # the axis needs to slew
            self.log.info("Wait for telescope elevation axis to finish slewing")
            data = await self.atmcs.evt_elevationInPosition.next(
                flush=False, timeout=SLEW_TIMEOUT
            )
            assert data.inPosition, "Got unexpected elevationInPosition event"
        data = self.atmcs.evt_azimuthInPosition.get()
        if not data.inPosition:
            self.log.info("Wait for telescope azimuth axis to finish slewing")
            data = await self.atmcs.evt_azimuthInPosition.next(
                flush=False, timeout=SLEW_TIMEOUT
            )
            assert data.inPosition, "Got unexpected azimuthInPosition event"

        # Check that the dome command still matches target azimuth
        # and that the dome has not moved significantly;
        # for the latter allow some slop
        dome_pos = await self.atdome.tel_position.next(flush=True, timeout=STD_TIMEOUT)
        try:
            await self.atdome.evt_azimuthCommandedState.next(flush=False, timeout=0.1)
        except asyncio.TimeoutError:
            # this is what we want: no new azimuthCommandedState event
            pass
        else:
            raise AssertionError("Dome moved unexpectedly")
        self.log.info(
            f"After telescope slew: "
            f"dome current azimuth={dome_pos.azimuthPosition:0.2f}"
        )
        assert (
            abs(salobj.angle_diff(dome_pos.azimuthPosition, self.track_elaz[1]).deg)
            <= 0.5
        ), (
            f"Dome dome azimuthPosition={dome_pos.azimuthPosition:0.2f} != "
            f"{self.track_elaz[1]:0.2f} = telescope target azimuth"
        )
        dome_cmd_az_before_big_move = dome_az_cmd_state.azimuth

        # Offset telescope azimuth relative to dome position
        # by more than the ATDomeTrajectory azimuth dead band/cos(el)
        # and verify that the commanded dome azimuth updates to match
        daz = scaled_atdometraj_max_az * 1.2
        if self.track_elaz[1] + daz >= self.config.azmax:
            daz = -daz
        self.offset_telescope_az(daz, "more than enough to move the dome")
        data = await self.atmcs.evt_azimuthInPosition.next(
            flush=False, timeout=SLEW_TIMEOUT
        )
        assert (
            not data.inPosition
        ), "Telescope azimuth in position but should be slewing"

        # Commanded dome azimuth should have changed
        dome_pos = await self.atdome.tel_position.next(flush=True, timeout=STD_TIMEOUT)
        dome_az_cmd_state = await self.atdome.evt_azimuthCommandedState.next(
            flush=False, timeout=STD_TIMEOUT
        )
        self.log.info(
            f"As large offset starts: "
            f"dome commanded state={dome_az_cmd_state.commandedState}; "
            f"commanded azimuth={dome_az_cmd_state.azimuth:0.2f}; "
            f"current azimuth={dome_pos.azimuthPosition:0.2f}"
        )
        assert dome_az_cmd_state.commandedState == AzimuthCommandedState.GOTOPOSITION, (
            f"ATDome azimuth commanded state={dome_az_cmd_state.commandedState} != "
            f"GoToPosition={AzimuthCommandedState.GOTOPOSITION}"
        )
        # use subtract_angles in case dome azimuth ~= 0
        assert (
            abs(
                salobj.angle_diff(
                    dome_az_cmd_state.azimuth, dome_cmd_az_before_big_move
                ).deg
            )
            >= 0.1
        ), (
            f"Dome commanded azimuth={dome_az_cmd_state.azimuth:0.2f} == "
            f"{dome_cmd_az_before_big_move:0.2f}=previous value "
        )
        data = await self.atdome.evt_azimuthState.next(flush=False, timeout=STD_TIMEOUT)
        if daz > 0:
            expected_az_state = AzimuthState.MOVINGCW
        else:
            expected_az_state = AzimuthState.MOVINGCCW
        assert (
            data.state == expected_az_state
        ), f"Dome azimuth state={data.state}; expected {expected_az_state}"

        data = await self.atmcs.evt_azimuthInPosition.next(
            flush=False, timeout=SLEW_TIMEOUT
        )
        assert (
            data.inPosition
        ), "Telescope azimuth not in position but slew should be done"

        dome_cmd_az_after_big_move = dome_az_cmd_state.azimuth

        # Wait for dome to finish moving
        data = await self.atdome.evt_azimuthState.next(
            flush=False, timeout=SLEW_TIMEOUT
        )
        assert data.state == AzimuthState.NOTINMOTION, (
            f"Dome azimuth state = {data.state}; expected "
            f"{AzimuthState.NOTINMOTION} = halted"
        )

        # Offset telescope azimuth by less than the ATDomeTrajectory
        # azimuth dead band and check that the dome does not move
        daz = atdometraj_max_az * 0.8
        if self.track_elaz[1] + daz >= self.config.azmax:
            daz = -daz
        self.offset_telescope_az(daz, "not enough to move the dome")
        data = await self.atmcs.evt_azimuthInPosition.next(
            flush=False, timeout=STD_TIMEOUT
        )
        assert (
            not data.inPosition
        ), "Telescope azimuth in position but should be slewing"

        # Commanded dome azimuth should not have changed
        dome_pos = await self.atdome.tel_position.next(flush=True, timeout=STD_TIMEOUT)
        self.log.info(
            f"As small offset starts: dome azimuth position={dome_pos.azimuthPosition:0.2f}"
        )
        try:
            await self.atdome.evt_azimuthCommandedState.next(flush=False, timeout=0.1)
        except asyncio.TimeoutError:
            # this is what we want: no new azimuthCommandedState event
            pass
        else:
            raise AssertionError("Dome moved unexpectedly")

        data = await self.atmcs.evt_azimuthInPosition.next(
            flush=False, timeout=SLEW_TIMEOUT
        )
        assert (
            data.inPosition
        ), "Telescope azimuth not in position but slew should be done"

        dome_pos = await self.atdome.tel_position.next(flush=True, timeout=STD_TIMEOUT)
        self.log.info(
            f"After small offset: dome azimuth position={dome_pos.azimuthPosition:0.2f}"
        )
        # use subtract_angles in case dome azimuth ~= 0
        assert (
            abs(
                salobj.angle_diff(
                    dome_pos.azimuthPosition, dome_cmd_az_after_big_move
                ).deg
            )
            <= 0.1
        ), (
            f"Dome azimuthPosition={dome_pos.azimuthPosition:0.2f} != "
            f"{dome_cmd_az_after_big_move:0.2f} = previous value "
        )
        try:
            await self.atdome.evt_azimuthCommandedState.next(flush=False, timeout=0.1)
        except asyncio.TimeoutError:
            # this is what we want: no new azimuthCommandedState event
            pass
        else:
            raise AssertionError("Dome moved unexpectedly")

        # Stop tracking
        self.log.info("Stop telescope tracking")
        self.stop_track_telescope()

        # Disable ATDomeTrajectory
        self.log.info("Disable ATDomeTrajectory")
        await salobj.set_summary_state(self.atdometraj, salobj.State.DISABLED)

    def offset_telescope_az(self, daz, reason):
        """Command ATMCS to offset by the specified amount in azimuth.

        Update self.track_elaz to the new target position.

        Parameters
        ----------
        daz : `float`
            Desired change in telescope azimuth (deg)
        reason : `str`
            Reason for offset (for a log message)

        Raises
        ------
        RuntimeError
            If not presently tracking.
        """
        if self._track_task is None or self._track_task.done():
            raise RuntimeError("Telescope is not tracking")
        self.log.info(f"Offset telescope azimuth by {daz:0.2f}: {reason}")
        self.track_elaz = (self.track_elaz[0], self.track_elaz[1] + daz)

    def track_telescope(self, el, az):
        """Command ATMCS to track a specified position.

        Set self.track_elaz to the target position,
        and start the tracking loop (if not running).

        Parameters
        ----------
        el : `float`
            Desired telescope elevation (deg)
        az : `float`
            Desired telescope azimuth (deg)
        """
        self.track_elaz = (el, az)
        if self._track_task is None or self._track_task.done():
            self._track_task = asyncio.ensure_future(self._track_telescope_loop())

    def stop_track_telescope(self):
        """Command ATMCS to stop tracking.
        """
        if self._track_task is None or self._track_task.done():
            return
        self._track_task.cancel()

    def set_metadata(self, metadata):
        metadata.duration = SLEW_TIMEOUT  # rough estimate

    async def _track_telescope_loop(self):
        """Telescope tracking loop.

        Enable ATMCS tracking and send ATMCS the target position specified by
        self.track_azel at regular intervals.
        When canceled stop ATMCS tracking.
        """
        await self.atmcs.cmd_startTracking.start(timeout=STD_TIMEOUT)
        try:
            while True:
                self.log.debug(
                    f"trackTarget: el={self.track_elaz[0]:0.2f}, az={self.track_elaz[1]:0.2f}"
                )
                self.atmcs.cmd_trackTarget.set(
                    elevation=self.track_elaz[0],
                    azimuth=self.track_elaz[1],
                    taiTime=salobj.current_tai(),
                )
                await self.atmcs.cmd_trackTarget.start(timeout=STD_TIMEOUT)
                await asyncio.sleep(TRACK_INTERVAL)
        except asyncio.CancelledError:
            pass

    async def cleanup(self):
        # Stop tracking
        self.log.info("cleanup")
        try:
            await self.atmcs.cmd_stopTracking.start(timeout=STD_TIMEOUT)
        except salobj.AckError as e:
            self.log.error(f"cleanup: ATMCS stopTracking failed with {e}")
        else:
            self.log.info("Stopped tracking in ATMCS")
