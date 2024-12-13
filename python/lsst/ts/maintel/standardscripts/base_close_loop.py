# This file is part of ts_externalcripts
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
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

__all__ = ["BaseCloseLoop"]

import abc
import asyncio
import types
import typing

import numpy as np
import yaml
from lsst.ts import salobj
from lsst.ts.observatory.control import BaseCamera
from lsst.ts.observatory.control.maintel.mtcs import MTCS
from lsst.ts.observatory.control.utils.enums import ClosedLoopMode, DOFName

STD_TIMEOUT = 10
CMD_TIMEOUT = 400


class BaseCloseLoop(salobj.BaseScript, metaclass=abc.ABCMeta):
    """Closed loop script. This script is used to perform measurements of
    the wavefront error, then propose dof offsets based on ts_ofc.

    Parameters
    ----------
    index : `int`, optional
        Index of Script SAL component (default=1).
    descr : `str`, optional
        Short description of the script.

    Notes
    -----
    **Checkpoints**

    - "Taking image...": If taking in-focus detection image.
    - "[N/MAX_ITER]: Closed loop starting...": Before each closed loop
        iteration, where "N" is the iteration number and "MAX_ITER"
        is the maximum number of iterations.
    - "[N/MAX_ITER]: Closed converged.": Once Closed Loop reaches convergence.
    - "[N/MAX_ITER]: Closed applying correction.": Just before
        corrections are applied.

    **Details**

    This script is used to perform measurements of the wavefront error, then
    propose dof offsets based on ts_ofc. The offsets are not applied
    automatically and must be turned on by the user through
    apply_corrections attribute.  if apply_corrections is off, the script
    will take a series of intra/extra focal data instead, and the number
    of pairs is the number of maximum iterations.
    """

    def __init__(self, index=1, descr="") -> None:
        super().__init__(
            index=index,
            descr=descr,
        )

        self.mtcs = None
        self._camera = None

        # The following attributes are set via the configuration
        self.filter = None

        # exposure time for the intra/extra images (in seconds)
        self.exposure_time = None
        self.n_images = 9

        # Define operation mode handler function
        self.operation_model_handlers = {
            ClosedLoopMode.CWFS: self.handle_cwfs_mode,
            ClosedLoopMode.FAM: self.handle_fam_mode,
        }

    @property
    def camera(self) -> BaseCamera:
        if self._camera is not None:
            return self._camera
        else:
            raise RuntimeError("Camera not defined.")

    @camera.setter
    def camera(self, value: BaseCamera | None) -> None:
        self._camera = value

    @abc.abstractmethod
    def configure_camera(self) -> None:
        raise NotImplementedError()

    @property
    @abc.abstractmethod
    def oods(self) -> None:
        raise NotImplementedError()

    async def configure_tcs(self) -> None:
        """Handle creating MTCS object and waiting for remote to start."""
        if self.mtcs is None:
            self.log.debug("Creating MTCS.")
            self.mtcs = MTCS(
                domain=self.domain,
                log=self.log,
            )
            await self.mtcs.start_task
        else:
            self.log.debug("MTCS already defined, skipping.")

    @classmethod
    def get_schema(cls) -> typing.Dict[str, typing.Any]:
        schema_yaml = f"""
            $schema: http://json-schema.org/draft-07/schema#
            $id: https://github.com/lsst-ts/ts_standardscripts/auxtel/BaseClosedLoop.yaml
            title: BaseClosedLoop v1
            description: Configuration for BaseClosedLoop Script.
            type: object
            properties:
              mode:
                description: >-
                    Mode to use for the script. If set to "cwfs", the script will
                    use the corner wavefront sensors, if set to "fam" the script
                    will use the full array mode.
                type: string
                enum: ["CWFS", "FAM"]
                default: CWFS
              filter:
                description: Which filter to use when taking intra/extra focal images.
                type: string
              exposure_time:
                description: The exposure time to use when taking images (sec).
                type: number
                default: 30.
              dz:
                description: De-focus to apply when acquiring the intra/extra focal images (microns).
                type: number
                default: 1500.
              threshold:
                description: >-
                    DOF threshold for convergence (um). If DOF offsets are
                    smaller than this value, the script will stop.
                type: array
                items:
                  type: number
                  minimum: 0
                minItems: 50
                maxItems: 50
                default: {[0.004]*50}
              max_iter:
                description:  >-
                    Maximum number of iterations.
                    Note, if apply_corrections is False, the script
                    will take [max_iter] pairs of images.
                type: integer
                default: 5
              program:
                description: >-
                    Optional name of the program this dataset belongs to.
                type: string
                default: CWFS
              reason:
                description: Optional reason for taking the data.
                anyOf:
                  - type: string
                  - type: "null"
                default: null
              note:
                description: A descriptive note about the image being taken.
                anyOf:
                  - type: string
                  - type: "null"
                default: null
              wep_config:
                description: Configuration for WEP pipeline. Optional.
                type: object
                additionalProperties: true
              used_dofs:
                oneOf:
                  - type: array
                    items:
                      type: integer
                      minimum: 0
                      maximum: 49
                  - type: array
                    items:
                      type: string
                      enum: {[dof_name.name for dof_name in DOFName]}
                default: [1, 2, 3, 4, 5]
              gain_sequence:
                description: >-
                    Gain sequence to apply to the offsets.
                oneOf:
                    - type: array
                      items:
                        type: number
                    - type: number
                default: 0
              apply_corrections:
                description: >-
                    Apply OFC corrections after each iteration.
                type: boolean
                default: true
              use_ocps:
                description: >-
                    Use OCPS to run the wavefront estimation pipeline.
                type: boolean
                default: true
              ignore:
                  description: >-
                      CSCs from the group to ignore in status check. Name must
                      match those in self.group.components, e.g.; hexapod_1.
                  type: array
                  items:
                      type: string
            additionalProperties: false
            required:
              - filter
        """
        return yaml.safe_load(schema_yaml)

    async def configure(self, config: types.SimpleNamespace) -> None:
        """Configure script.

        Parameters
        ----------
        config : `types.SimpleNamespace`
            Script configuration, as defined by `schema`.
        """

        # Configure tcs and camera
        await self.configure_tcs()
        await self.configure_camera()

        # Set mode
        self.mode = getattr(ClosedLoopMode, config.mode)

        # Set filter
        self.filter = config.filter

        # Set exposure time
        self.exposure_time = config.exposure_time

        # Set intra/extra focal offsets
        self.dz = config.dz

        # Set threshold
        self.threshold = config.threshold

        # Set maximum number of iterations
        self.max_iter = config.max_iter

        # Set program and reason
        self.reason = config.reason
        self.program = config.program
        self.note = config.note

        # Set WEP configuration string in yaml format
        self.wep_config = yaml.dump(getattr(config, "wep_config", {}))
        self.use_ocps = config.use_ocps

        # Set used dofs
        selected_dofs = config.used_dofs
        if isinstance(selected_dofs[0], str):
            selected_dofs = [getattr(DOFName, dof) for dof in selected_dofs]
        self.used_dofs = np.zeros(50)
        self.used_dofs[selected_dofs] = 1

        # Set apply_corrections
        self.apply_corrections = config.apply_corrections

        self.gain_sequence = config.gain_sequence

        if hasattr(config, "ignore"):
            self.mtcs.disable_checks_for_components(components=config.ignore)

    def set_metadata(self, metadata: salobj.type_hints.BaseMsgType) -> None:
        """Sets script metadata.

        Parameters
        ----------
        metadata : `salobj.type_hints.BaseMsgType`
            Script metadata topic. The information is set on the topic
            directly.
        """
        # Estimated duration is maximum number of iterations multiplied by
        # the time it takes to take the data (2 images) plus estimation on
        # processing the data (10s), plus time it takes to take final
        # acquisition image

        metadata.duration = (
            self.camera.filter_change_timeout
            + self.max_iter
            * (
                self.exposure_time
                + self.camera.read_out_time
                + self.camera.shutter_time
            )
            * (2 if self.mode == ClosedLoopMode.CWFS else 1)
            + self.camera.read_out_time
            + self.camera.shutter_time
        )
        metadata.filter = f"{self.filter}"

    async def take_intra_extra_focal_images(
        self,
        supplemented_group_id: str,
    ) -> typing.Tuple[typing.Any, typing.Any]:
        """Take intra and extra focal images.

        Returns
        -------
        intra_image : `typing.Any`
            Intra focal image.
        extra_image : `typing.Any`
            Extra focal image.
        """

        # Take intra focal image
        self.log.debug("Moving to intra-focal position")

        await self.mtcs.offset_camera_hexapod(x=0, y=0, z=-self.dz, u=0, v=0)

        self.log.debug("Taking intra-focal image")

        intra_image = await self.camera.take_cwfs(
            exptime=self.exposure_time,
            n=1,
            group_id=supplemented_group_id,
            filter=self.filter,
            reason="INTRA" + ("" if self.reason is None else f"_{self.reason}"),
            program=self.program,
            note=self.note,
        )

        self.log.debug("Moving to extra-focal position")

        # Hexapod offsets are relative, so need to move 2x the offset
        # to get from the intra- to the extra-focal position.
        z_offset = self.dz * 2.0
        await self.mtcs.offset_camera_hexapod(x=0, y=0, z=z_offset, u=0, v=0)

        self.log.debug("Taking extra-focal image")

        self.oods.evt_imageInOODS.flush()
        # Take extra-focal iamge
        extra_image = await self.camera.take_cwfs(
            exptime=self.exposure_time,
            n=1,
            group_id=supplemented_group_id,
            filter=self.filter,
            reason="EXTRA" + ("" if self.reason is None else f"_{self.reason}"),
            program=self.program,
            note=self.note,
        )

        task1 = self.wait_for_images_in_oods()
        # Move the hexapod back to in focus position
        task2 = self.mtcs.offset_camera_hexapod(x=0, y=0, z=-self.dz, u=0, v=0)
        await asyncio.gather(task1, task2)

        return intra_image, extra_image

    async def wait_for_images_in_oods(self):

        for _ in range(self.n_images):
            try:
                image_in_oods = await self.oods.evt_imageInOODS.next(
                    flush=False, timeout=self.exposure_time
                )
                self.log.info(
                    f"Image {image_in_oods.obsid} {image_in_oods.raft} {image_in_oods.sensor} ingested."
                )
            except asyncio.TimeoutError:
                self.log.warning("Timeout waiting for images in OODS.")

    async def handle_fam_mode(self, supplemented_group_id: str) -> None:
        """Handle Full Array Mode."""

        # Take intra and extra focal images
        intra_image, extra_image = await self.take_intra_extra_focal_images(
            supplemented_group_id
        )

        # Set intra and extra visit id
        intra_visit_id = int(intra_image[0])
        extra_visit_id = int(extra_image[0])

        take_infocus_image_task = asyncio.create_task(
            self.camera.take_acq(
                self.exposure_time,
                group_id=supplemented_group_id,
                reason="INFOCUS" + ("" if self.reason is None else f"_{self.reason}"),
                program=self.program,
                filter=self.filter,
                note=self.note,
            )
        )

        # Run WEP
        await self.mtcs.rem.mtaos.cmd_runWEP.set_start(
            visitId=intra_visit_id,
            extraId=extra_visit_id,
            useOCPS=self.use_ocps,
            config=self.wep_config,
            timeout=2 * CMD_TIMEOUT,
        )
        await take_infocus_image_task

    async def handle_cwfs_mode(self, supplemented_group_id: str) -> None:
        """Handle CWFS mode."""

        # Take in-focus image
        image = await self.camera.take_acq(
            self.exposure_time,
            group_id=supplemented_group_id,
            reason="INFOCUS" + ("" if self.reason is None else f"_{self.reason}"),
            program=self.program,
            filter=self.filter,
            note=self.note,
        )

        # Set visit id
        visit_id = int(image[0])

        # Run WEP
        await self.mtcs.rem.mtaos.cmd_runWEP.set_start(
            visitId=visit_id, timeout=2 * CMD_TIMEOUT, config=self.wep_config
        )

    async def compute_ofc_offsets(self, rotation_angle: float, gain: float) -> None:
        """Compute offsets using ts_ofc.

        Parameters
        ----------
        rotation_angle : `float`
            Rotation angle of the camera in deg.
        gain : `float`
            Gain to apply to the offsets.
        """
        # Create the config to run OFC
        config = {
            "filter_name": self.filter,
            "rotation_angle": rotation_angle,
            "comp_dof_idx": {
                "m2HexPos": [float(val) for val in self.used_dofs[:5]],
                "camHexPos": [float(val) for val in self.used_dofs[5:10]],
                "M1M3Bend": [float(val) for val in self.used_dofs[10:30]],
                "M2Bend": [float(val) for val in self.used_dofs[30:]],
            },
        }
        config_yaml = yaml.safe_dump(config)

        # Run OFC
        self.mtcs.rem.mtaos.evt_degreeOfFreedom.flush()
        await self.mtcs.rem.mtaos.cmd_runOFC.set_start(
            config=config_yaml, timeout=CMD_TIMEOUT, userGain=gain
        )

        # Return offsets
        return await self.mtcs.rem.mtaos.evt_degreeOfFreedom.next(
            flush=False, timeout=STD_TIMEOUT
        )

    def get_gain(self, iteration: int) -> float:
        """Get the gain to apply to the offsets.

        Parameters
        ----------
        iteration : `int`
            Iteration number.

        Returns
        -------
        gain : `float`
            Gain to apply to the offsets.
        """
        if isinstance(self.gain_sequence, float) or isinstance(self.gain_sequence, int):
            return float(self.gain_sequence)
        else:
            if iteration >= len(self.gain_sequence):
                self.log.warning(
                    "Iteration is greater than the length of the gain sequence. "
                    "Using the last value of the gains sequence."
                )
                return self.gain_sequence[-1]
            return self.gain_sequence[iteration]

    async def arun(self, checkpoint: bool = False) -> None:
        """Perform wavefront error measurements and DOF adjustments until the
        thresholds are reached.

        Parameters
        ----------
        checkpoint : `bool`, optional
            Should issue checkpoints

        Raises
        ------
        RuntimeError:
            If coordinates are malformed.
        """

        for i in range(self.max_iter):
            self.log.debug(f"Closed Loop iteration {i + 1} starting...")

            if checkpoint:
                await self.checkpoint(
                    f"[{i + 1}/{self.max_iter}]: Closed Loop loop starting..."
                )

                await self.checkpoint(f"[{i + 1}/{self.max_iter}]: Taking image...")

            # Flush wavefront error topic
            self.mtcs.rem.mtaos.evt_wavefrontError.flush()

            # Retrieve the rotation angle before taking data.
            start_rotation_angle = await self.mtcs.rem.mtrotator.tel_rotation.next(
                flush=True, timeout=STD_TIMEOUT
            )

            # Run the operational mode handler function.
            await self.operation_model_handlers[self.mode](
                self.next_supplemented_group_id()
            )

            # Retrieve the rotation angle after taking data.
            end_rotation_angle = await self.mtcs.rem.mtrotator.tel_rotation.next(
                flush=True, timeout=STD_TIMEOUT
            )

            # Compute average rotation angle while taking data
            rotation_angle = (
                start_rotation_angle.actualPosition + end_rotation_angle.actualPosition
            ) / 2

            # Save the wavefront error
            wavefront_error = await self.mtcs.rem.mtaos.evt_wavefrontError.next(
                flush=False, timeout=STD_TIMEOUT
            )

            self.log.info(
                f"Wavefront error zernike coefficients: {wavefront_error} in um."
            )

            # Compute ts_ofc offsets
            dof_offset = await self.compute_ofc_offsets(
                rotation_angle, self.get_gain(i)
            )

            # If apply_corrections is true,
            # then we apply the corrections
            if self.apply_corrections:
                self.log.info("Applying corrections...")

                if checkpoint:
                    await self.checkpoint(
                        f"[{i + 1}/{self.max_iter}]: Applying correction."
                    )

                # Apply ts_ofc corrections
                await self.mtcs.rem.mtaos.cmd_issueCorrection.start(timeout=CMD_TIMEOUT)

            # Check if corrections have converged. If they have, then we stop.
            if all(np.abs(dof_offset.visitDoF) < self.threshold):
                self.log.info(f"OFC offsets are inside tolerance ({self.threshold}). ")
                if checkpoint:
                    await self.checkpoint(
                        f"[{i + 1}/{self.max_iter}]: Closed Loop converged."
                    )

                self.log.info("Closed Loop completed successfully!")
                return

        # If we reach the maximum number of iterations without
        # converging, then we stop.
        self.log.warning(
            f"Reached maximum iteration ({self.max_iter}) without convergence.\n"
        )

    async def assert_feasibility(self) -> None:
        """Verify that the telescope and camera are in a feasible state to
        execute the script.
        """
        await self.mtcs.assert_all_enabled()
        await self.camera.assert_all_enabled()

    async def assert_mode_compatibility(self) -> None:
        """Verify that the script mode is compatible with the camera.
        Defaults to pass. It is only overriden by ComCam, since it
        only allows for FAM."""

        pass

    async def run(self) -> None:
        """Execute script.

        This method simply call `arun` with `checkpoint=True`.
        """

        await self.assert_feasibility()
        await self.assert_mode_compatibility()

        await self.arun(True)
