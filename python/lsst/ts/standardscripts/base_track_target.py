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
# along with this program. If not, see <https://www.gnu.org/licenses/>.

__all__ = ["BaseTrackTarget"]

import abc
import asyncio
import enum

import yaml
from lsst.ts.idl.enums.Script import ScriptState
from lsst.ts.observatory.control.utils import RotType
from lsst.ts.xml.enums.MTPtg import Planets

from .base_block_script import BaseBlockScript


class SlewType(enum.IntEnum):
    OBJECT = enum.auto()
    ICRS = enum.auto()
    AZEL = enum.auto()
    PLANET = enum.auto()
    EPHEM = enum.auto()
    TRACK_AZEL = enum.auto()


class BaseTrackTarget(BaseBlockScript, metaclass=abc.ABCMeta):
    """Base track target script.

    This script implements the basic configuration and run procedures for
    slewing and tracking a target, either by using ICRS coordinates or the
    object name. It is a base class for both the Main and Auxiliary Telescope.

    Parameters
    ----------
    index : `int`
        Index of Script SAL component.
    descr : `str`
        Short Script description.

    """

    def __init__(self, index, descr):
        super().__init__(index=index, descr=descr)

        self.config = None

        # Flag to monitor if tracking started for cleanup task.
        self.tracking_started = False

        # Flag to specify which type of slew will be performend:
        # slew_icrs, slew_object, slew_planet or slew_ephem
        self.slew_type = SlewType.OBJECT

        # Timeout for slewing (in seconds).
        self.slew_timeout = 240.0

    @property
    @abc.abstractmethod
    def tcs(self):
        raise NotImplementedError()

    async def configure_tcs(self):
        if self.tcs is not None:
            await self.tcs.start_task

    @classmethod
    def get_schema(cls):
        planet_names = ", ".join([f'"{planet.name}"' for planet in Planets])

        schema_yaml = f"""
            $schema: http://json-schema.org/draft-07/schema#
            $id: https://github.com/lsst-ts/ts_standardscripts/base_slew.yaml
            title: BaseTrackTarget v1
            description: Configuration for BaseTrackTarget.
            type: object
            properties:
              slew_icrs:
                type: object
                description: >-
                    Optional configuration section. Slew to icrs ra/dec coordinates.
                    If not specified it will be ignored.
                additionalProperties: false
                required:
                    - ra
                    - dec
                properties:
                  ra:
                    description: ICRS right ascension (hour).
                    anyOf:
                      - type: number
                        minimum: 0
                        maximum: 24
                      - type: string
                  dec:
                    description: ICRS declination (deg).
                    anyOf:
                      - type: number
                        minimum: -90
                        maximum: 90
                      - type: string
              track_azel:
                type: object
                description: >-
                    Optional configuration section. Slew to az/el and start tracking.
                    If not specified it will be ignored.
                additionalProperties: false
                required:
                    - az
                    - el
                properties:
                  az:
                    description: Azimuth (deg).
                    anyOf:
                      - type: number
                      - type: string
                  el:
                    description: Elevation (deg).
                    anyOf:
                      - type: number
                        minimum: 0
                        maximum: 90
                      - type: string
              slew_planet:
                type: object
                description: >-
                    Optional configuration section. Slew to a Solar system planet.
                    If not specified it will be ignored. If specified, the rot_type
                    propertie must be Sky.
                additionalProperties: false
                properties:
                  planet_name:
                    description: The name of a Solar system planet.
                    type: string
                    enum: [{planet_names}]
              slew_ephem:
                type: object
                description: >-
                    Optional configuration section. Slew to a target based on
                    ephemeris data. If not specified it will be ignored.
                additionalProperties: false
                properties:
                  ephem_file:
                    description: Ephemeris filename to be used for the slew.
                    type: string
                  object_name:
                    description: The name of object.
                    type: string
              find_target:
                type: object
                additionalProperties: false
                required:
                  - az
                  - el
                  - mag_limit
                description: >-
                    Optional configuration section. Find a target to perform CWFS in the given
                    position and magnitude range. If not specified, the step is ignored.
                properties:
                  az:
                    type: number
                    description: Azimuth (in degrees) to find a target.
                  el:
                    type: number
                    description: Elevation (in degrees) to find a target.
                  mag_limit:
                    type: number
                    description: Minimum (brightest) V-magnitude limit.
                  mag_range:
                    type: number
                    description: >-
                        Magnitude range. The maximum/faintest limit is defined as
                        mag_limit+mag_range.
                  radius:
                    type: number
                    description: Radius of the cone search (in degrees).
              offset:
                type: object
                additionalProperties: false
                description: >-
                    Optional configuration section. Apply offset in xy to the original
                    pointing position.
                properties:
                  x:
                    type: number
                    description: Offset the field in the x-axis (arcsec).
                    default: 0
                  y:
                    type: number
                    description: Offset the field in the y-axis (arcsec).
                    default: 0
              differential_tracking:
                description: Differential tracking rates.
                type: object
                additionalProperties: false
                properties:
                  dra:
                    description: Differential tracking rate in RA (sec/sec).
                    type: number
                    default: 0.0
                  ddec:
                    description: Differential tracking rate in Declination (arcsec/sec).
                    type: number
                    default: 0.0
              rot_value:
                description: >-
                  Rotator position value. Actual meaning depends on rot_type.
                type: number
                default: 0
              rot_type:
                description: >-
                  Rotator strategy. Options are:
                    Sky: Sky position angle strategy. The rotator is positioned with respect
                         to the North axis so rot_angle=0. means y-axis is aligned with North.
                         Angle grows clock-wise.

                    SkyAuto: Same as sky position angle but it will verify that the requested
                             angle is achievable and wrap it to a valid range.

                    Parallactic: This strategy is required for taking optimum spectra with
                                 LATISS. If set to zero, the rotator is positioned so that the
                                 y-axis (dispersion axis) is aligned with the parallactic
                                 angle.

                    PhysicalSky: This strategy allows users to select the **initial** position
                                  of the rotator in terms of the physical rotator angle (in the
                                  reference frame of the telescope). Note that the telescope
                                  will resume tracking the sky rotation.

                    Physical: Select a fixed position for the rotator in the reference frame of
                              the telescope. Rotator will not track in this mode.
                type: string
                enum: ["Sky", "SkyAuto", "Parallactic", "PhysicalSky", "Physical"]
                default: SkyAuto
              target_name:
                description: Target name
                type: string
              track_for:
                description: >-
                    How long to track target for (in seconds). If zero, the default,
                    finish script as soon as in position, otherwise, continue tracking
                    target until time expires.
                type: number
                minimum: 0
                default: 0
              stop_when_done:
                description: >-
                    Stop tracking once tracking time expires. Only valid if
                    `track_for` is larger than zero.
                type: boolean
                default: False
              az_wrap_strategy:
                description: >-
                  Azimuth wrapping strategy. Options are:
                    MAXTIMEONTARGET: Maximize the tracking time on the target.

                    NOUNWRAP: Do not attempt to unwrap. If target is unreachable
                    without unwrapping, command will be rejected.

                    OPTIMIZE: Use `track_for` to determine if there is
                    enough time left without unwrapping and only unwrap if
                    needed.
                type: string
                enum: ["MAXTIMEONTARGET", "NOUNWRAP", "OPTIMIZE"]
                default: OPTIMIZE
              slew_timeout:
                description: Timeout for slew procedure (in seconds).
                type: number
                default: 240.0
              ignore:
                description: >-
                    CSCs from the group to ignore in status check. Name must
                    match those in self.group.components, e.g.; hexapod_1.
                type: array
                items:
                    type: string
            if:
              properties:
                slew_icrs:
                  const: null
                track_azel:
                  const: null
                slew_planet:
                  const: null
                slew_ephem:
                  const: null
            then:
              oneOf:
                - required:
                  - target_name
                - required:
                  - find_target
            else:
              oneOf:
                - required:
                  - slew_icrs
                - required:
                  - track_azel
                - required:
                  - slew_planet
                - required:
                  - slew_ephem
            additionalProperties: false
        """
        schema_dict = yaml.safe_load(schema_yaml)

        base_schema_dict = super().get_schema()

        for properties in base_schema_dict["properties"]:
            schema_dict["properties"][properties] = base_schema_dict["properties"][
                properties
            ]

        return schema_dict

    async def configure(self, config):
        """Configure the script.

        Parameters
        ----------
        config : `types.SimpleNamespace`
            Configuration
        """

        self.config = config

        if hasattr(self.config, "slew_icrs"):
            self.slew_type = SlewType.ICRS
        elif hasattr(self.config, "track_azel"):
            self.slew_type = SlewType.TRACK_AZEL
        elif hasattr(self.config, "slew_planet"):
            self.slew_type = SlewType.PLANET
        elif hasattr(self.config, "slew_ephem"):
            self.slew_type = SlewType.EPHEM
        elif hasattr(self.config, "find_target"):
            self.slew_type = SlewType.AZEL

        self.log.debug(f"Slew type: {self.slew_type!r}.")

        await self.configure_tcs()

        self.config.rot_type = getattr(RotType, self.config.rot_type)

        if (
            self.slew_type == SlewType.PLANET or self.slew_type == SlewType.EPHEM
        ) and self.config.rot_type != RotType.Sky:
            self.log.warning(
                f"Slew_type={self.slew_type!r} only works for {RotType.Sky!r}, "
                f"got {self.config.rot_type!r}. Ignoring."
            )

        self.config.az_wrap_strategy = getattr(
            self.tcs.WrapStrategy, self.config.az_wrap_strategy
        )

        if hasattr(self.config, "ignore"):
            self.tcs.disable_checks_for_components(components=config.ignore)
        else:
            self.log.info(f"Not ignoring TCS components: {self.tcs.components_attr}.")

        await super().configure(config=config)

    def set_metadata(self, metadata):
        """Compute estimated duration.

        Parameters
        ----------
        metadata : `Script_logevent_metadata`
        """
        metadata.duration = 10.0 + self.config.track_for

    async def run_block(self):
        target_name = getattr(self.config, "target_name", "slew_icrs")

        self.tracking_started = True

        offset_x = self.config.offset["x"]
        offset_y = self.config.offset["y"]
        dra = self.config.differential_tracking["dra"]
        ddec = self.config.differential_tracking["ddec"]

        if self.slew_type == SlewType.ICRS:
            ra = self.config.slew_icrs["ra"]
            dec = self.config.slew_icrs["dec"]

            self.log.info(
                f"Slew and track target_name={target_name}; "
                f"ra={ra}, dec={dec}; "
                f"rot={self.config.rot_value}; rot_type={self.config.rot_type}; "
                f"offset by; x={offset_x}; y={offset_y}"
            )

            await self.tcs.slew_icrs(
                ra=ra,
                dec=dec,
                rot=self.config.rot_value,
                rot_type=self.config.rot_type,
                target_name=target_name,
                dra=dra,
                ddec=ddec,
                offset_x=offset_x,
                offset_y=offset_y,
                az_wrap_strategy=self.config.az_wrap_strategy,
                time_on_target=self.config.track_for,
                slew_timeout=self.slew_timeout,
            )

        elif self.slew_type == SlewType.TRACK_AZEL:
            az = self.config.track_azel["az"]
            el = self.config.track_azel["el"]

            self.log.info(
                f"Slew and track at "
                f"az={az}, el={el}; "
                f"rot={self.config.rot_value}; rot_type={self.config.rot_type}; "
                f"offset by; x={offset_x}; y={offset_y}"
            )

            await self.tcs.point_azel(
                az=az,
                el=el,
                rot_tel=self.config.rot_value,
            )
            await self.tcs.start_tracking()

        elif self.slew_type == SlewType.PLANET:
            planet_name = self.config.slew_planet["planet_name"]
            planet_enum = Planets[planet_name]

            self.log.info(
                f"Slew and track planet_name={planet_name}; rot_sky={self.config.rot_value}."
                f"offset by; x={offset_x}; y={offset_y}"
            )

            await self.tcs.slew_to_planet(
                planet=planet_enum,
                rot_sky=self.config.rot_value,
                slew_timeout=self.slew_timeout,
            )

        elif self.slew_type == SlewType.EPHEM:
            ephem_file = self.config.slew_ephem["ephem_file"]
            object_name = self.config.slew_ephem["object_name"]

            self.log.info(
                f"Slew and track object_name={object_name}; "
                f"ephem_file={ephem_file}; rot_sky={self.config.rot_value}; "
                f"offset by; x={offset_x}; y={offset_y}"
            )

            await self.tcs.slew_ephem_target(
                ephem_file=self.config.slew_ephem["ephem_file"],
                target_name=self.config.slew_ephem["object_name"],
                rot_sky=self.config.rot_value,
                slew_timeout=self.slew_timeout,
            )

        elif self.slew_type == SlewType.AZEL:
            az = self.config.find_target["az"]
            el = self.config.find_target["el"]

            self.log.info(
                "Find target around azel; "
                f"az={az}, el={el}; "
                f"rot={self.config.rot_value}; rot_type={self.config.rot_type}; "
                f"offset by; x={offset_x}; y={offset_y}"
            )
            try:
                self.tcs.load_catalog("HD_cwfs_stars")
            except Exception:
                self.log.exception("Failed to load local star catalog. Ignoring.")

            target_name = await self.tcs.find_target(**self.config.find_target)

            await self.tcs.slew_object(
                name=target_name,
                rot=self.config.rot_value,
                rot_type=self.config.rot_type,
                dra=dra,
                ddec=ddec,
                offset_x=offset_x,
                offset_y=offset_y,
                az_wrap_strategy=self.config.az_wrap_strategy,
                time_on_target=self.config.track_for,
                slew_timeout=self.slew_timeout,
            )
        else:
            self.log.info(
                f"Slew and track target_name={target_name}; "
                f"rot={self.config.rot_value}; rot_type={self.config.rot_type}; "
                f"offset by; x={offset_x}; y={offset_y}"
            )
            await self.tcs.slew_object(
                name=target_name,
                rot=self.config.rot_value,
                rot_type=self.config.rot_type,
                dra=dra,
                ddec=ddec,
                offset_x=offset_x,
                offset_y=offset_y,
                az_wrap_strategy=self.config.az_wrap_strategy,
                time_on_target=self.config.track_for,
                slew_timeout=self.slew_timeout,
            )

        if self.config.track_for > 0.0:
            self.log.info(f"Tracking for {self.config.track_for}s .")
            await self.tcs.check_tracking(self.config.track_for)
            if self.config.stop_when_done:
                self.log.info("Tracking completed. Stop tracking.")
                await self.tcs.stop_tracking()
            else:
                self.log.info("Tracking completed.")

    async def cleanup(self):
        if self.state.state != ScriptState.ENDING:
            # abnormal termination
            if self.tracking_started:
                self.log.warning(
                    f"Terminating with state={self.state.state}: stop tracking."
                )
                try:
                    await asyncio.wait_for(self.tcs.stop_tracking(), timeout=5)
                except asyncio.TimeoutError:
                    self.log.exception(
                        "Stop tracking command timed out during cleanup procedure."
                    )
                except Exception:
                    self.log.exception("Unexpected exception in stop_tracking.")
