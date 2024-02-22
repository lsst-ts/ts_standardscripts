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

    def __init__(self, camera, config, identifier):
        self.camera = camera
        self.config = config
        self.identifier = identifier


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
                  required:
                    - index
                    - exp_times
                    - image_type
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
        and an arbitrary number of Generic Cameras.

        Parameters
        ----------
        config : `types.SimpleNamespace`
            Configuration namespace containing camera-specific configurations.

        Notes
        -----
        - `self.mtcs`: An instance of the MTCS. Initialized
        only once and used to control telescope components beyond cameras.

        - `self.camera_setups`: A dictionary of `CameraSetup` instances.
          Each instance encapsulates a camera object (ComCam, LSSTCam,
          orGenericCamera), its specific imaging configuration, and an
          identifier.

        The method ensures that MTCS and each camera are initialized only once.
        For generic cameras, initialization tasks are executed concurrently to
        optimize startup time.
        """

        self.config = config

        # Check that program configuration has a dash
        if hasattr(config, "program") and "-" not in config.program:
            raise ValueError(
                "Program name requires a dash separating program from id number "
                "(e.g. TEST-123)."
            )

        # Initialize MTCS if not already done
        if self.mtcs is None:
            self.log.debug("Creating MTCS.")
            self.mtcs = MTCS(domain=self.domain, log=self.log)
            await self.mtcs.start_task
        else:
            self.log.debug("MTCS already defined, skipping.")

        # Initialize or update  LSSTCam if configured
        if "lsstcam" not in self.camera_setups and hasattr(config, "lsstcam"):
            self.log.debug("Creating LSSTCam.")
            lsstcam = LSSTCam(self.domain, log=self.log)
            await lsstcam.start_task
            self.camera_setups["lsstcam"] = CameraSetup(
                lsstcam, config.lsstcam, "LSSTCam"
            )
        elif hasattr(config, "lsstcam"):
            self.log.debug("LSSTCam already defined, updating configuration.")
            self.camera_setups["lsstcam"].config = config.lsstcam

        # Initialize or update  ComCam if configured
        if "comcam" not in self.camera_setups and hasattr(config, "comcam"):
            self.log.debug("Creating ComCam.")
            comcam = ComCam(self.domain, log=self.log)
            await comcam.start_task
            self.camera_setups["comcam"] = CameraSetup(comcam, config.comcam, "ComCam")
        elif hasattr(config, "comcam"):
            self.log.debug("ComCam already defined, updating configuration.")
            self.camera_setups["comcam"].config = config.comcam

        # Initialize or update Generic Cameras if configured
        if hasattr(config, "gencam"):
            # Prepare tasks for initializing or updating generic cameras
            init_update_tasks = [
                self.init_or_update_gencam(gencam_config)
                for gencam_config in config.gencam
            ]

            # Execute tasks concurrently
            await asyncio.gather(*init_update_tasks)

        await super().configure(config=config)

    async def init_or_update_gencam(self, gencam_config):
        """Initialize or update a generic camera."""
        # Key used in self.camera_setups
        gencam_key = f"generic_camera_{gencam_config['index']}"
        # Identifier used in CameraSetup
        gencam_identifier = f"GenericCam_{gencam_config['index']}"

        if gencam_key not in self.camera_setups:
            self.log.debug(f"Creating {gencam_identifier}.")
            gencam = GenericCamera(
                gencam_config["index"], domain=self.domain, log=self.log
            )
            await gencam.start_task
            self.camera_setups[gencam_key] = CameraSetup(
                gencam, gencam_config, gencam_identifier
            )
        else:
            self.log.debug(
                f"{gencam_identifier} already defined, updating configuration."
            )
            self.camera_setups[gencam_key].config = gencam_config

    def set_metadata(self, metadata: type_hints.BaseMsgType) -> None:
        """Set script metadata."""
        if not self.camera_setups:  # Ensure we have camera setups
            metadata.duration = 0
            return

        camera_durations = {}
        for camera_setup in self.camera_setups.values():
            if len(camera_setup.config) != 0:
                self.log.info(
                    f"{camera_setup.identifier} configuration: "
                    f"{camera_setup.config}"
                )
                exp_times = (
                    camera_setup.config["exp_times"]
                    if "exp_times" in camera_setup.config
                    else 0
                )
                nimages = len(exp_times) if isinstance(exp_times, list) else 1
                total_exptime = (
                    sum(exp_times) if isinstance(exp_times, list) else exp_times
                )
                read_out_time = getattr(camera_setup.camera, "read_out_time", 0)
                shutter_time = getattr(camera_setup.camera, "shutter_time", 0)

                duration = (
                    self.instrument_setup_time
                    + total_exptime
                    + (read_out_time + shutter_time * 2) * nimages
                )
                camera_durations[camera_setup.identifier] = duration

        # Safeguard against empty sequences
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
        if hasattr(camera_config, "filter"):
            instrument_config["filter"] = camera_config["filter"]
        return instrument_config

    async def assert_feasibility(self):
        """
        Verify that the system and all configured cameras are in a
        feasible state to execute the script.
        """
        checks = [self.mtcs.assert_liveliness()]

        for camera_setup in self.camera_setups.values():
            if hasattr(camera_setup.camera, "assert_all_enabled"):
                checks.append(camera_setup.camera.assert_all_enabled())
            if hasattr(camera_setup.camera, "assert_liveliness"):
                checks.append(camera_setup.camera.assert_liveliness())

        await asyncio.gather(*checks)

    def normalize_exp_times(self, exp_times):
        """Ensure exp_times is always a list for consistent processing."""
        return exp_times if isinstance(exp_times, list) else [exp_times]

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

            exp_times = self.normalize_exp_times(camera_setup.config["exp_times"])
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
                    image_type=image_type,
                    exp_time=exp_time,
                    note=note,
                    reason=reason,
                    program=program,
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
