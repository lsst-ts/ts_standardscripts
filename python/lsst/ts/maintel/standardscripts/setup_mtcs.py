# This file is part of ts_maintel_standardscripts
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
# along with this program. If not, see <https://www.gnu.org/licenses/>.

__all__ = ["SetupMTCS"]

import pandas as pd
import yaml
from lsst.ts import salobj
from lsst.ts.observatory.control.maintel.mtcs import MTCS, MTCSUsages


class SetupMTCS(salobj.BaseScript):
    """Setup MTCS components so they are ready for operation.

    The script starts with MTPtg, MTMount, and MTRotator.
    Then, checks if the camera-cable-wrap (CCW) is following the Rotator.
    It also checks the telemetry from these components.

    After that, it points the mount to the Zenith so we can raise M1M3 safely.
    M1M3 is enabled, raised and the corrections are enabled and reset.
    We do the same for M2, Camera Hexapod and Rotator Hexapod.

    Finally, it enables MTAOS, MTDomeTrajectory and MTDome.

    Parameters
    ----------
    index : `int`
        Index of Script SAL component.

    Notes
    -----
    **Checkpoints**

    (none)

    **Details**

    This script starts them in the following order:
      - mtptg
      - mtmount
      - mtrotator
      - mtm1m3
      - mtm2
      - mthexapod_1 (camera hexpapod)
      - mthexapod_2 (m2 hexapod)
      - all the other components (mtaos / mtdome / mtdometrajectory)

    """

    def __init__(self, index=1, remotes: bool = True):
        super().__init__(
            index=index,
            descr="Setup MTCS components for operations.",
        )
        self.activity_estimated_duration = dict(
            enable_components=dict(time=5.0, repeats=8),  # Enable components
            move_to_zenith=dict(time=10.0, repeats=1),  # Move mount to zenith
            raise_m1m3=dict(time=600.0, repeats=1),  # Raise m1m3
            enable_corrections=dict(time=5.0, repeats=4),  # Enable/reset corrections
            get_telemetry=dict(time=5.0, repeats=6),  # Timeout extracting telemetries
        )

        self.config = None
        self.mtcs = (
            MTCS(domain=self.domain, log=self.log)
            if remotes
            else MTCS(
                domain=self.domain, log=self.log, intended_usage=MTCSUsages.DryTest
            )
        )

        self.checkpoints_activities = [
            ("Check that MTCS Components have heartbeats", self.mtcs.assert_liveliness),
            ("Start MTPtg", self.start_mtptg),
            ("Prepare MTMount and MTRotator", self.prepare_mtmount_and_mtrotator),
            ("Start MTMount", self.start_mtmount),
            ("Start MTRotator", self.start_mtrotator),
            ("Check Rotator and CCW", self.check_rotator_and_ccw),
            ("Start MTM1M3", self.start_mtm1m3),
            ("Start MTM2", self.start_mtm2),
            ("Start Camera Hexapod", self.start_camera_hexapod),
            ("Start M2 Hexapod", self.start_m2_hexapod),
            ("Enable remaining components", self.mtcs.enable),
        ]

    @classmethod
    def get_schema(cls):
        id_url = (
            "https://github.com/lsst-ts/ts_stardardscripts/blob/master/"
            "python/lsst/ts/externalscripts/maintel/setup_mtcs.py"
        )

        schema = f"""
        $schema: http://json-schema.org/draft-07/schema#
        $id: {id_url}
        title: SetupMTCS v1
        description: Configuration for SetupMTCS SAL Script.
        type: object
        additionalProperties: false
        properties:
          ccw_following:
            description: >-
              enable ccw following mode? (default: True)
            type: boolean
            default: true
          overrides:
            description: Overrides configurations for different components.
            type: object
            additionalProperties: false
            properties:
              mtptg:
                description: Override configuration for MTPtg.
                anyOf:
                  - type: string
                  - type: "null"
                default: null
              mtmount:
                description: Override configuration for MTMount.
                anyOf:
                  - type: string
                  - type: "null"
                default: null
              mtrotator:
                description: Override configuration for MTRotator.
                anyOf:
                  - type: string
                  - type: "null"
                default: null
              mtm1m3:
                description: Override configuration for MTM1M3.
                anyOf:
                  - type: string
                  - type: "null"
                default: Default
              mtm2:
                description: Override configuration for MTM2.
                anyOf:
                  - type: string
                  - type: "null"
                default: null
              mthexapod_1:
                description: Override configuration for Camera Hexapod.
                anyOf:
                  - type: string
                  - type: "null"
                default: null
              mthexapod_2:
                description: Override configuration for M2 Hexapod.
                anyOf:
                  - type: string
                  - type: "null"
                default: null
        """
        return yaml.safe_load(schema)

    async def configure(self, config):
        """Handle script input configuration.

        Parameters
        ----------
        config: `types.SimpleNamespace`
          Configuration data. See `get_schema` for information about data
          structure.
        """
        self.log.debug(f"Enable CCW following: {config.ccw_following}")
        self.config = config

    def set_metadata(self, metadata):
        """Set estimated duration of the script."""
        metadata.duration = sum(
            [
                self.activity_estimated_duration[action]["time"]
                * self.activity_estimated_duration[action]["repeats"]
                for action in self.activity_estimated_duration
            ]
        )

    async def run(self):
        """Runs the script"""
        for checkpoint, activity in self.checkpoints_activities:
            await self.checkpoint(checkpoint)
            await activity()

        await self.checkpoint("Done")

    async def start_mtptg(self):
        """Starts mtptg"""
        self.log.info("Start mtptg")
        await self.mtcs.set_state(
            salobj.State.ENABLED,
            components=["mtptg"],
            overrides=dict(mtptg=self.config.overrides["mtptg"]),
        )

    async def prepare_mtmount_and_mtrotator(self):
        """Put both mtmount and mtrotator in DISABLED state. This is required
        before enabling them because they share telemetry."""
        self.log.info("Putting mtmount to DISABLED state")
        await self.mtcs.set_state(
            salobj.State.DISABLED,
            components=["mtmount"],
            overrides=dict(mtmount=self.config.overrides["mtmount"]),
        )
        self.log.info("Putting mtrotator to DISABLED state")
        await self.mtcs.set_state(
            salobj.State.DISABLED,
            components=["mtrotator"],
            overrides=dict(mtmount=self.config.overrides["mtmount"]),
        )

    async def start_mtmount(self):
        """Starts mtmount"""
        self.log.info("Start mtmount")
        await self.mtcs.set_state(
            salobj.State.ENABLED,
            components=["mtmount"],
            overrides=dict(mtmount=self.config.overrides["mtmount"]),
        )
        # TODO: DM-36932
        self.log.info("Home mtmount")
        await self.mtcs.rem.mtmount.cmd_homeBothAxes.start(timeout=300)

    async def start_mtrotator(self):
        """Start mtrotator"""
        self.log.info("Start mtrotator")
        await self.mtcs.set_state(
            salobj.State.ENABLED,
            components=["mtrotator"],
            overrides=dict(mtmount=self.config.overrides["mtrotator"]),
        )

        state = await self.mtcs.get_state("mtrotator")
        self.log.info(f" mtrotator is now in {state.name}")

    async def check_rotator_and_ccw(self):
        """Check the telemetry from the Rotator and the Camera-Cable-Wrap to
        make sure that they can be operated together."""
        timeout = self.activity_estimated_duration["get_telemetry"]["time"]

        elevation = await self.mtcs.rem.mtmount.tel_elevation.next(
            flush=True, timeout=timeout
        )
        azimuth = await self.mtcs.rem.mtmount.tel_azimuth.next(
            flush=True, timeout=timeout
        )
        ccw = await self.mtcs.rem.mtmount.tel_cameraCableWrap.next(
            flush=True, timeout=timeout
        )
        rotator = await self.mtcs.rem.mtrotator.tel_rotation.next(
            flush=True, timeout=timeout
        )

        self.log.info(
            f"mount elevation Angle = {elevation.actualPosition} \n"
            f"mount azimuth angle = {azimuth.actualPosition}\n"
            f"CCW angle = {ccw.actualPosition}.\n"
            f"rot angle = {rotator.actualPosition}\n"
            f"diff = {rotator.actualPosition - ccw.actualPosition}\n"
        )

        ccw_following = await self.mtcs.rem.mtmount.evt_cameraCableWrapFollowing.aget(
            timeout=timeout
        )

        timestamp = pd.to_datetime(ccw_following.private_sndStamp, unit="s")

        # We actually want CCW following
        if self.config.ccw_following:
            # If as expected
            if ccw_following.enabled:
                self.log.info(
                    f"CCW following mode enabled: "
                    f"{ccw_following.enabled} @ {timestamp}."
                )

            # Otherwise
            else:
                await self.mtcs.set_state(salobj.State.DISABLED, components=["mtmount"])
                raise RuntimeError(
                    "CCW following mode not enabled. "
                    "Usually this means that the MTMount could not see"
                    " telemetry from the rotator when it was enabled. "
                    "To correct this condition make sure the MTRotator telemetry"
                    " is being published, then execute the procedure again. "
                    "MTMount CSC will be left in DISABLED state."
                )

        # We decided *not* to use CCW following
        else:
            await self.mtcs.disable_ccw_following()

        ccw = await self.mtcs.rem.mtmount.tel_cameraCableWrap.next(
            flush=True, timeout=timeout
        )

        rotator = await self.mtcs.rem.mtrotator.tel_rotation.next(
            flush=True, timeout=timeout
        )

        ccw_snd_stamp = pd.to_datetime(ccw.private_sndStamp, unit="s")
        ccw_timestamp = pd.to_datetime(ccw.timestamp, unit="s")
        ccw_actual_position = ccw.actualPosition

        rotator_snd_stamp = pd.to_datetime(rotator.private_sndStamp, unit="s")
        rotator_timestamp = pd.to_datetime(rotator.timestamp, unit="s")
        rotator_actual_position = rotator.actualPosition

        self.log.info(
            f"CCW:: snd_stamp={ccw_snd_stamp} "
            f"timestamp={ccw_timestamp} "
            f"actual position={ccw_actual_position}"
        )

        self.log.info(
            f"Rotator:: snd_stamp={rotator_snd_stamp} "
            f"timestamp={rotator_timestamp} "
            f"actual position={rotator_actual_position}"
        )

        ccw_telemetry_maximum_age = pd.to_timedelta(1.0, unit="s")

        if abs(ccw_snd_stamp - ccw_timestamp) > ccw_telemetry_maximum_age:
            self.log.warning(
                f"CCW timestamp out of sync by "
                f"{abs(ccw_snd_stamp - ccw_timestamp)}s. "
                f"System may not work. Check clock synchronization in MTMount "
                f"low level controller."
            )

    async def start_mtm1m3(self):
        """Start mtm1m3"""
        self.log.info("Starting M1M3")
        self.log.info("Moving telescope to zenith to safely raise the mirror.")
        await self.mtcs.rem.mtmount.cmd_moveToTarget.set_start(azimuth=0, elevation=90)

        await self.mtcs.set_state(
            state=salobj.State.ENABLED,
            components=["mtm1m3"],
            overrides=dict(mtm1m3="Default"),
        )

        self.log.info("Raising M1M3")
        await self.mtcs.raise_m1m3()

        self.log.info("M1M3 - Enable and reset balance forces")
        await self.mtcs.enable_m1m3_balance_system()
        await self.mtcs.reset_m1m3_forces()

    async def start_mtm2(self):
        """Start MTM2"""
        await self.mtcs.set_state(
            state=salobj.State.ENABLED,
            components=["mtm2"],
            overrides=dict(mtm2=self.config.overrides["mtm2"]),
        )
        await self.mtcs.enable_m2_balance_system()
        await self.mtcs.reset_m2_forces()

    async def start_mthexapod(self, index):
        """Start MTHexapod for the Camera or for M2

        Parameters
        ----------
        index : int, {1, 2}
            Index associated to the hexapod CSC.
            1 = camera hexapod
            2 = m2 hexapod
        """
        assert index in [1, 2]
        component = f"mthexapod_{index}"

        await self.mtcs.set_state(
            state=salobj.State.ENABLED,
            components=[component],
            overrides={component: self.config.overrides[component]},
        )

        await self.mtcs.enable_compensation_mode(component=component)

        if index == 1:
            await self.mtcs.reset_camera_hexapod_position()
        else:
            await self.mtcs.reset_m2_hexapod_position()

    async def start_camera_hexapod(self):
        """Starts the Camera Hexapod"""
        await self.start_mthexapod(index=1)

    async def start_m2_hexapod(self):
        """Starts the M2 Hexapod"""
        await self.start_mthexapod(index=2)
