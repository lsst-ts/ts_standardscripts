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

__all__ = ["TakeImageAnyCam", "CameraSetup"]

import asyncio

import yaml
from lsst.ts.observatory.control.generic_camera import GenericCamera
from lsst.ts.observatory.control.maintel import MTCS
from lsst.ts.observatory.control.maintel.comcam import ComCam
from lsst.ts.observatory.control.maintel.lsstcam import LSSTCam
from lsst.ts.salobj import type_hints

from ..base_block_script import BaseBlockScript


class CameraSetup:
    """
    Encapsulates camera object, its configuration,
    and a unique identifier.
    """

    def __init__(self, camera, config, identifier, normalize=True):
        self.camera = camera
        self.identifier = identifier
        if normalize:
            self.config = self.normalize_config(config)
        else:
            self.config = config

    @staticmethod
    def normalize_config(config):
        """Normalize the camera configuration for consistent processing."""

        # If 'nimages' is provided along with 'exp_times' as a list,
        # raise an error.
        if isinstance(config.get("exp_times"), list) and "nimages" in config:
            raise ValueError("If 'nimages' is provided, 'exp_times' must be a scalar.")

        # If 'exp_times' is a scalar (including 0 or positive values) and
        # 'nimages' is specified, expand 'exp_times' into a list with 'nimages'
        # repetitions.
        elif not isinstance(config.get("exp_times"), list) and "nimages" in config:
            nimages = config["nimages"]
            exp_times = config.get("exp_times", 0)  # Default to 0 if not provided
            config["exp_times"] = [exp_times] * nimages

        # If 'exp_times' is a scalar and 'nimages' is not provided,
        # transform 'exp_times' into a list with a single element.
        elif not isinstance(config.get("exp_times"), list):
            exp_times = config.get("exp_times", 0)  # Default to 0 if not provided
            config["exp_times"] = [exp_times]

        return config


class TakeImageAnyCam(BaseBlockScript):
    """
    A script for taking images concurrently with ComCam,
    LSSTCam, and/or one or more Generic Cameras.

    Parameters
    ----------
    index : `int`
        Index of Script SAL component.

    Notes
    -----
    **Checkpoints**

    * Setup instrument: before sending the ``setup_instrument`` command
      for each configure camera.

    * Total expected duration: {x}s for {longest_camera_duration} taking
      {total_exposures} images: before starting exposures.

    * Exposing image {i} of {n} with exp_time={exp_time}s for {camera}: before
      each exposure for the longest duration camera."

    """

    def __init__(self, index: int) -> None:
        super().__init__(
            index,
            descr="Concurrently take images with either ComCam or LSSTCam, "
            "and Generic Cameras.",
        )

        self.mtcs = None
        self.camera_setups = {}

        self.camera_longest = None
        self.camera_longest_duration = 0.0
        self.instrument_setup_time = 0.0

    @classmethod
    def get_schema(cls):
        schema_yaml = """
            $schema: http://json-schema.org/draft-07/schema#
            $id: https://github.com/lsst-ts/ts_standardscripts/take_image_anycam.yaml
            title: TakeImageAnyCam
            description: Configuration schema for TakeImageAnyCam.
            type: object
            properties:
              comcam:
                description: Configuration for ComCam.
                type: object
                properties:
                  exp_times:
                    description: A list of exposure time of each image (sec).
                    oneOf:
                      - type: number
                        minimum: 0
                      - type: array
                        items:
                          type: number
                          minimum: 0
                        minItems: 1
                  nimages:
                    description: Optional number of images to take. If given, exp_times must be a scalar.
                      If given and exp_times is a list, it raises an error.
                    anyOf:
                      - type: integer
                        minimum: 1
                      - type: "null"
                  image_type:
                    description: Image type (a.k.a. IMGTYPE) (e.g. e.g. BIAS, DARK, FLAT, OBJECT)
                    type: string
                    enum: ["BIAS", "DARK", "FLAT", "OBJECT", "ENGTEST", "ACQ", "CWFS", "FOCUS", "STUTTERED"]
                  filter:
                    description: Filter name or ID; if omitted the filter is not changed.
                    anyOf:
                      - type: string
                      - type: integer
                        minimum: 1
                      - type: "null"
                required:
                  - exp_times
                  - image_type
              lsstcam:
                description: Configuration for ComCam.
                type: object
                properties:
                  exp_times:
                    description: A list of exposure time of each image (sec).
                    oneOf:
                      - type: number
                        minimum: 0
                      - type: array
                        items:
                          type: number
                          minimum: 0
                        minItems: 1
                  nimages:
                    description: Optional number of images to take. If given, exp_times must be a scalar.
                      If given and exp_times is a list, it raises an error.
                    anyOf:
                      - type: integer
                        minimum: 1
                      - type: "null"
                  image_type:
                    description: Image type (a.k.a. IMGTYPE) (e.g. e.g. BIAS, DARK, FLAT, OBJECT)
                    type: string
                    enum: ["BIAS", "DARK", "FLAT", "OBJECT", "ENGTEST", "ACQ", "CWFS", "FOCUS", "STUTTERED"]
                  filter:
                    description: Filter name or ID; if omitted the filter is not changed.
                    anyOf:
                      - type: string
                      - type: integer
                        minimum: 1
                      - type: "null"
                required:
                  - exp_times
                  - image_type
              gencam:
                description: Configuration for generic cameras.
                type: array
                items:
                  description: Configuration for each generic camera.
                  type: object
                  properties:
                    index:
                      description: Index of the Generic Camera SAL component.
                      type: integer
                      enum: [101, 102, 103]
                    exp_times:
                      description: A list of exposure time of each image (sec).
                      oneOf:
                        - type: number
                          minimum: 0
                        - type: array
                          items:
                            type: number
                            minimum: 0
                          minItems: 1
                    nimages:
                      description: Optional number of images to take. If given, exp_times must be a scalar.
                        If given and exp_times is a list, it raises an error.
                      anyOf:
                        - type: integer
                          minimum: 1
                        - type: "null"
                    image_type:
                      description: Image type (a.k.a. IMGTYPE) (e.g. e.g. BIAS, DARK, FLAT, OBJECT)
                      type: string
                      enum: ["BIAS", "DARK", "FLAT", "OBJECT", "ENGTEST", "ACQ", "CWFS", "FOCUS", "STUTTERED"]
                  required:
                    - index
                    - exp_times
                    - image_type
              ignore:
                  description: >-
                      CSCs from the group to ignore in status check. Name must
                      match those in self.group.components, e.g.; hexapod_1.
                  type: array
                  items:
                      type: string
              reason:
                description: Optional reason for taking the data (e.g. SITCOM-321).
                type: string
              program:
                description: Name of the program this data belongs to. Program name
                  requires a dash separaing program from id number (e.g. BLOCK-123).
                type: string
              note:
                description: A descriptive note about the image being taken.
                type: string
            additionalProperties: false
            required: []
            anyOf:
              - required: ["gencam"]
              - required: ["comcam"]
              - required: ["lsstcam"]
              - required: ["comcam", "gencam"]
              - required: ["lsstcam", "gencam"]
        """

        schema_dict = yaml.safe_load(schema_yaml)

        # ComCam and LTTScam are mutually exclusive
        if "comcam" in schema_dict and "filter" not in schema_dict["comcam"]:
            schema_dict["comcam"]["filter"] = None

        if "lsstcam" in schema_dict and "filter" not in schema_dict["lsstcam"]:
            schema_dict["lsstcam"]["filter"] = None

        base_schema_dict = super().get_schema()

        for properties in base_schema_dict["properties"]:
            schema_dict["properties"][properties] = base_schema_dict["properties"][
                properties
            ]

        return schema_dict

    async def configure(self, config):
        """Configure the script based on the provided configuration.

        This method initializes the MTCS and any cameras specified in the
        configuration (`config`). It supports initializing ComCam, LSSTCam,
        and the Generic Cameras.

        Raises
        ------
        ValueError
            If `nimages` is provided and `exp_times` is not a scalar.
        """

        self.config = config

        # Check that program configuration has a dash
        if hasattr(config, "program") and "-" not in config.program:
            raise ValueError(
                "Program name requires a dash separating program from id number "
                "(e.g. BLOCK-123)."
            )

        # Initialize MTCS if not already done
        if self.mtcs is None:
            self.mtcs = MTCS(domain=self.domain, log=self.log)
            await self.mtcs.start_task

        # Ignoring components
        if hasattr(self.config, "ignore"):
            self.mtcs.disable_checks_for_components(components=config.ignore)

        # Initialize cameras and set configuration
        await self.configure_cameras(config)

        await super().configure(config=config)

    async def configure_cameras(self, config):
        """Configure all cameras based on the script configuration,
        with asynchronous setup for generic cameras."""
        tasks = []
        if hasattr(config, "lsstcam"):
            tasks.append(
                self.configure_camera(
                    CameraClass=LSSTCam,
                    cam_key="lsstcam",
                    cam_config=config.lsstcam,
                    cam_identifier="LSSTCam",
                )
            )
        if hasattr(config, "comcam"):
            tasks.append(
                self.configure_camera(
                    CameraClass=ComCam,
                    cam_key="comcam",
                    cam_config=config.comcam,
                    cam_identifier="ComCam",
                )
            )
        if hasattr(config, "gencam"):
            for gencam_config in config.gencam:
                gencam_key = f"generic_camera_{gencam_config['index']}"
                gen_cam_identifier = f"GenericCam_{gencam_config['index']}"
                tasks.append(
                    self.configure_camera(
                        CameraClass=GenericCamera,
                        cam_key=gencam_key,
                        cam_config=gencam_config,
                        cam_identifier=gen_cam_identifier,
                        is_generic=True,
                    )
                )
        await asyncio.gather(*tasks)

    async def configure_camera(
        self, CameraClass, cam_key, cam_config, cam_identifier, is_generic=False
    ):
        """Configure a specific camera."""

        if cam_key not in self.camera_setups:
            camera = (
                CameraClass(domain=self.domain, log=self.log)
                if not is_generic
                else CameraClass(cam_config["index"], domain=self.domain, log=self.log)
            )
            await camera.start_task
            # Setting up the camera.
            self.camera_setups[cam_key] = CameraSetup(
                camera, cam_config, cam_identifier
            )
        else:
            # upating the camera configuration if already defined.
            self.camera_setups[cam_key].config = CameraSetup.normalize_config(
                cam_config
            )

    def set_metadata(self, metadata: type_hints.BaseMsgType) -> None:
        """Set script metadata."""
        if not self.camera_setups:  # Ensure we have camera setups
            metadata.duration = 0
            return

        camera_durations = {}
        for camera_setup in self.camera_setups.values():
            if camera_setup.config:
                self.log.info(
                    f"{camera_setup.identifier} configuration: {camera_setup.config}"
                )
                exp_times = camera_setup.config["exp_times"]
                nimages = len(exp_times)
                total_exptime = sum(exp_times)
                read_out_time = getattr(camera_setup.camera, "read_out_time", 0)
                shutter_time = getattr(camera_setup.camera, "shutter_time", 0)

                duration = (
                    self.instrument_setup_time
                    + total_exptime
                    + (read_out_time + shutter_time * 2) * nimages
                )
                camera_durations[camera_setup.identifier] = duration
                self.log.info(
                    f"{camera_setup.identifier} will take {nimages} images. Total duration: {duration}."
                )

        if camera_durations:
            self.camera_longest, self.camera_longest_duration = max(
                camera_durations.items(), key=lambda item: item[1]
            )
        else:
            self.camera_longest, self.camera_longest_duration = None, 0

        metadata.duration = self.camera_longest_duration

    def get_instrument_configuration(self, camera_config: dict) -> dict:
        # Ensure the return value is always a dictionary
        instrument_config = {}
        if "filter" in camera_config:
            instrument_config["filter"] = camera_config["filter"]
        return instrument_config

    async def assert_feasibility(self):
        """Verify that the system and all configured cameras are in
        a feasible state to execute the script."""
        checks = [self.mtcs.assert_liveliness()]
        for camera_setup in self.camera_setups.values():
            if hasattr(camera_setup.camera, "assert_all_enabled"):
                checks.append(camera_setup.camera.assert_all_enabled())
            if hasattr(camera_setup.camera, "assert_liveliness"):
                checks.append(camera_setup.camera.assert_liveliness())
        await asyncio.gather(*checks)

    async def take_images_with_camera(self, camera_setup: CameraSetup):
        """
        Commands a specified camera to take images according to
        its configuration.

        Parameters
        ----------
        camera_config : CameraSetup
            An object containing the camera instance, its configuration,
            and a unique identifier.
        """

        if len(camera_setup.config) != 0:
            exp_times = camera_setup.config["exp_times"]
            image_type = camera_setup.config["image_type"]
            note = getattr(self.config, "note", None)
            reason = getattr(self.config, "reason", None)
            program = getattr(self.config, "program", None)

            # Assert feasibility before taking images with the camera
            await self.assert_feasibility()

            instrument_config = self.get_instrument_configuration(camera_setup.config)
            if hasattr(camera_setup.camera, "setup_instrument"):
                await self.checkpoint(
                    f"Setup instrument for {camera_setup.identifier}."
                )
                await camera_setup.camera.setup_instrument(**instrument_config)

            for i, exp_time in enumerate(exp_times):
                if camera_setup.identifier == self.camera_longest:
                    await self.checkpoint(
                        f"Exposing image {i+1} of {len(exp_times)} with "
                        f"exp_time={exp_time}s for {camera_setup.identifier}."
                    )
                await camera_setup.camera.take_imgtype(
                    imgtype=image_type,
                    exptime=exp_time,
                    n=1,
                    program=program,
                    reason=reason,
                    note=note,
                    group_id=self.group_id,
                )

    async def run_block(self):
        """
        Executes the image capture tasks concurrently for all
        configured cameras.
        """
        tasks = []

        longest_camera_setup = self.camera_setups.get(self.camera_longest, None)

        if longest_camera_setup:
            total_exposures = len(longest_camera_setup.config["exp_times"])
            self.checkpoint(
                f"Total expected duration: {self.camera_longest_duration:.2f} s "
                f"for {self.camera_longest} taking {total_exposures} images."
            )

        # Prepare tasks for each configured camera
        for camera_setup in self.camera_setups.values():
            tasks.append(self.take_images_with_camera(camera_setup))

        # Execute all image capture tasks simultaneously
        await asyncio.gather(*tasks)
