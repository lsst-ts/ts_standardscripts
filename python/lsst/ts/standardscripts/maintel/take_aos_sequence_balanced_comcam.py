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

__all__ = ["TakeAOSSequenceBalancedComCam"]

import asyncio
import json

from lsst.ts.standardscripts.maintel import Mode, TakeAOSSequenceComCam


class TakeAOSSequenceBalancedComCam(TakeAOSSequenceComCam):
    """Take aos sequence, either triplet (intra-focal, extra-focal
    and in-focus images), intra doublets (intra and in-focus) or extra
    doublets (extra and in-focus) sequences with ComCam.

    This version splits the dz offset evenly between the camera and M2
    hexapods.

    Parameters
    ----------
    index : `int`
        Index of Script SAL component.

    Notes
    -----
    **Checkpoints**

    * sequence {n} of {m}: before taking a sequence.

    """
    
    async def take_aos_sequence(self) -> None:
        """Take out-of-focus sequence images."""
        supplemented_group_id = self.next_supplemented_group_id()

        if (
            self.mode == Mode.TRIPLET
            or self.mode == Mode.INTRA
            or self.mode == Mode.PAIR
        ):
            self.log.debug("Moving to intra-focal position")

            # Move the camera and M2 hexapods to the target z position
            # Offset split in half and shared between each hexapod
            z_offset = (-self.dz - self.current_z_position) / 2
            await self.mtcs.offset_camera_hexapod(x=0, y=0, z=z_offset, u=0, v=0)
            await self.mtcs.offset_m2_hexapod(x=0, y=0, z=z_offset, u=0, v=0)
            self.current_z_position = -self.dz

            self.log.info("Taking intra-focal image")
            self.camera.rem.ccoods.evt_imageInOODS.flush()
            intra_visit_id = await self.camera.take_cwfs(
                exptime=self.exposure_time,
                n=1,
                group_id=supplemented_group_id,
                filter=self.filter,
                reason="INTRA" + ("" if self.reason is None else f"_{self.reason}"),
                program=self.program,
                note=self.note,
            )

        if (
            self.mode == Mode.TRIPLET
            or self.mode == Mode.EXTRA
            or self.mode == Mode.PAIR
        ):
            self.log.debug("Moving to extra-focal position")

            # Move the camera and M2 hexapods to the target z position
            # Offset split in half and shared between each hexapod
            z_offset = (self.dz - self.current_z_position) / 2
            await self.mtcs.offset_camera_hexapod(x=0, y=0, z=z_offset, u=0, v=0)
            await self.mtcs.offset_m2_hexapod(x=0, y=0, z=z_offset, u=0, v=0)
            self.current_z_position = self.dz

            self.log.info("Taking extra-focal image")

            self.camera.rem.ccoods.evt_imageInOODS.flush()
            extra_visit_id = await self.camera.take_cwfs(
                exptime=self.exposure_time,
                n=1,
                group_id=supplemented_group_id,
                filter=self.filter,
                reason="EXTRA" + ("" if self.reason is None else f"_{self.reason}"),
                program=self.program,
                note=self.note,
            )

        if self.mode == Mode.TRIPLET or self.mode == Mode.PAIR:
            self.log.debug("Waiting for images to be ingested in OODS.")
            extra_image_ingested = False
            while not extra_image_ingested:
                try:
                    image_in_oods = await self.camera.rem.ccoods.evt_imageInOODS.next(
                        flush=False, timeout=self.exposure_time
                    )
                    try:
                        image_name_split = image_in_oods.obsid.split("_")
                        image_index = int(
                            f"{image_name_split[-2]}{image_name_split[-1][1:]}"
                        )
                        extra_image_ingested = image_index == extra_visit_id[0]
                    except Exception:
                        self.log.exception(
                            "Failed to parse image name into index for {image_in_oods.obsid}."
                        )

                    self.log.info(
                        f"Image {image_in_oods.obsid} {image_in_oods.raft} {image_in_oods.sensor} ingested."
                    )

                except asyncio.TimeoutError:
                    self.log.warning(
                        "Timeout waiting for images to ingest. Continuing."
                    )
                    break
            self.log.info("Send processing request to RA OCPS.")
            config = {
                "LSSTComCam-FROM-OCS_DONUTPAIR": f"{intra_visit_id[0]},{extra_visit_id[0]}"
            }
            ocps_execute_task = asyncio.create_task(
                self.ocps.cmd_execute.set_start(
                    config=json.dumps(config),
                    timeout=self.camera.fast_timeout,
                )
            )

        self.log.debug("Moving to in-focus position")

        # Move the camera and M2 hexapods to the target z position
        # Offset split in half and shared between each hexapod
        z_offset = (-self.current_z_position) / 2
        await self.mtcs.offset_camera_hexapod(x=0, y=0, z=z_offset, u=0, v=0)
        await self.mtcs.offset_m2_hexapod(x=0, y=0, z=z_offset, u=0, v=0)
        self.current_z_position = 0

        if self.mode != Mode.PAIR:
            self.log.info("Taking in-focus image")
            self.camera.rem.ccoods.evt_imageInOODS.flush()
            await self.camera.take_acq(
                exptime=self.exposure_time,
                n=1,
                group_id=self.group_id,
                filter=self.filter,
                reason="INFOCUS" + ("" if self.reason is None else f"_{self.reason}"),
                program=self.program,
                note=self.note,
            )

        if self.mode == Mode.TRIPLET:
            try:
                await ocps_execute_task
            except Exception:
                self.log.exception("Executing OCPS task failed. Ignoring.")
                