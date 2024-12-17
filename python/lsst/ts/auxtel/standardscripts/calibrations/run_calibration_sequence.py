# This file is part of ts_externalscripts
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

__all__ = [
    "RunCalibrationSequence",
]

import hashlib
import io
import json

import yaml
from lsst.ts import utils
from lsst.ts.observatory.control.auxtel.atcalsys import ATCalsys
from lsst.ts.observatory.control.auxtel.latiss import LATISS
from lsst.ts.standardscripts import BaseBlockScript
from lsst.ts.standardscripts.utils import get_s3_bucket


class RunCalibrationSequence(BaseBlockScript):
    """Run calibration sequence with LATISS using ATCalSys."""

    def __init__(self, index: int) -> None:

        super().__init__(
            index=index,
            descr="Run calibration sequence with LATISS using ATCalSys.",
        )

        self.latiss = None
        self.atcalsys = None

        self.sequence_name = None

        self.sequence_summary = dict()
        self.exposure_metadata = dict()

    @classmethod
    def get_schema(cls):
        yaml_schema = """
        $schema: http://json-schema/draft-07/schema#
        $id: https://github.com/lsst-ts/ts_externalscripts/auxtel/LatissTakeFlats.yaml
        title: LatissTakeFlats v1
        description: Configuration for LatissTakeFlats.
        type: object
        properties:
            sequence_name:
                description: >-
                    Name of the calibration sequence that will be taken.
                    It must match an existing label in the ATCalSys calibration configuration file.
        required: [sequence_name]
        additionalProperties: false
            """
        schema_dict = yaml.safe_load(yaml_schema)

        base_schema_dict = super().get_schema()

        for properties in base_schema_dict["properties"]:
            schema_dict["properties"][properties] = base_schema_dict["properties"][
                properties
            ]

        return schema_dict

    def set_metadata(self, metadata):
        metadata.duration = 600  # set arbitrarily

    async def configure(self, config):
        """Configure script.

        Parameters
        ----------
        config : `types.SimpleNamespace`
            Script configuration, as defined by `schema`.
        """
        self.log.debug(f"Configuration: {config}")

        self.sequence_name = config.sequence_name

        if self.latiss is None:
            self.log.debug("Creating LATISS.")
            self.latiss = LATISS(domain=self.domain, log=self.log)
            await self.latiss.start_task

        if self.atcalsys is None:
            self.log.debug("Creating ATCalSys.")
            self.atcalsys = ATCalsys(
                domain=self.domain, log=self.log, latiss=self.latiss
            )
            await self.atcalsys.start_task

        self.atcalsys.load_calibration_config_file()
        self.atcalsys.assert_valid_configuration_option(name=self.sequence_name)
        self.exposure_metadata["note"] = getattr(config, "note", None)
        self.exposure_metadata["reason"] = getattr(config, "reason", None)
        self.exposure_metadata["program"] = getattr(config, "program", None)
        await super().configure(config=config)

    async def prepare_summary_table(self):
        """Prepare final summary table.

        Checks writing is possible and that s3 bucket can be made
        """

        # Take a copy as the starting point for the summary
        self.sequence_summary = {}

        # Add metadata from this script
        date_begin = utils.astropy_time_from_tai_unix(utils.current_tai()).isot
        self.sequence_summary["date_begin_tai"] = date_begin
        self.sequence_summary["script_index"] = self.salinfo.index

    async def publish_sequence_summary(self):
        """Write sequence summary to LFA as a json file"""

        try:
            sequence_summary_payload = json.dumps(self.sequence_summary).encode()
            file_object = io.BytesIO()
            byte_size = file_object.write(sequence_summary_payload)
            file_object.seek(0)

            s3bucket = get_s3_bucket()

            key = s3bucket.make_key(
                salname=self.salinfo.name,
                salindexname=self.salinfo.index,
                generator="publish_sequence_summary",
                date=utils.astropy_time_from_tai_unix(utils.current_tai()),
                other=self.obs_id,
                suffix=".json",
            )

            await s3bucket.upload(fileobj=file_object, key=key)

            url = f"{s3bucket.service_resource.meta.client.meta.endpoint_url}/{s3bucket.name}/{key}"

            md5 = hashlib.md5()
            md5.update(sequence_summary_payload)

            await self.evt_largeFileObjectAvailable.set_write(
                id=self.obs_id,
                url=url,
                generator="publish_sequence_summary",
                mimeType="JSON",
                byteSize=byte_size,
                checkSum=md5.hexdigest(),
                version=1,
            )

        except Exception:
            msg = "Failed to save summary table."
            self.log.exception(msg)
            raise RuntimeError(msg)

    async def run_block(self):

        self.log.info(f"Preparing ATCalSys for sequence {self.sequence_name}.")

        await self.atcalsys.prepare_for_flat(sequence_name=self.sequence_name)

        await self.prepare_summary_table()

        self.exposure_metadata["group_id"] = (
            self.group_id if self.obs_id is None else self.obs_id
        )

        self.log.info(f"Running {self.sequence_name} calibration sequence.")

        sequence_summary = await self.atcalsys.run_calibration_sequence(
            sequence_name=self.sequence_name,
            exposure_metadata=self.exposure_metadata,
        )

        self.sequence_summary.update(sequence_summary)

        await self.publish_sequence_summary()
