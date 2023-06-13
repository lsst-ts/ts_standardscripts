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
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

__all__ = ["BaseBlockScript"]

import abc
import contextlib
import hashlib
import io
import json
import os
from datetime import datetime

import yaml
from lsst.ts import salobj, utils

from .utils import get_s3_bucket

IMAGE_SERVER_URL = dict(
    tucson="http://comcam-mcm.tu.lsst.org",
    base="http://lsstcam-mcm.ls.lsst.org",
    summit="http://139.229.170.11",
)


class BaseBlockScript(salobj.BaseScript, metaclass=abc.ABCMeta):
    """Extend BaseScript to add support for executing blocks.

    This base class adds a default configuration with reason and program that
    can be provided when executing the script.
    """

    def __init__(self, index: int, descr: str, help: str = "") -> None:
        super().__init__(index, descr, help)

        self.program = None
        self.reason = None
        self.obs_id = None
        self.checkpoint_message = None

        # Index generator.
        self.step_counter = None

        self.step_results = []

    @classmethod
    def get_schema(cls):
        schema_yaml = """
        $schema: http://json-schema.org/draft-07/schema#
        $id: https://github.com/lsst-ts/ts_standardscripts/base_block_script.py
        title: BaseBlockScript v1
        description: Configuration for Base Block Script.
        type: object
        properties:
            program:
                type: string
                description: >-
                    Program this script is related to. If this has the format of a block program (e.g.
                    BLOCK-NNNN, where N is an integer value), it will be used to generate an ID for the
                    script execution. A warning message is issued if this is provided in with any different
                    format. If this is not provided but test_case name is provided, it will be used here
                    instead.
            reason:
                type: string
                description: Reason for executing this script.
            test_case:
                type: object
                description: Test case information.
                additionalProperties: false
                properties:
                    name:
                        type: string
                        description: Test case related to this script execution.
                    execution:
                        type: string
                        description: Test case execution this script is related to.
                    version:
                        type: string
                        description: Version of the test case.
                    initial_step:
                        type: integer
                        description: >-
                            Initial step of the test case. If not given, use 1.
                    project:
                        type: string
                        description: >-
                            Name of the project hosting the test cases. If not given use LVV.
                required:
                    - name
                    - execution
                    - version
        additionalProperties: false
        """
        return yaml.safe_load(schema_yaml)

    async def configure(self, config):
        """Configure script.

        Parameters
        ----------
        config : `types.SimpleNamespace`
            Script configuration, as defined by `schema`.
        """
        self.program = getattr(config, "program", None)
        self.reason = getattr(config, "reason", None)
        self.test_case = getattr(config, "test_case", None)
        self.step_counter = (
            utils.index_generator(imin=self.test_case.get("initial_step", 1))
            if self.test_case is not None
            else None
        )

        if self.program is not None:
            self.checkpoint_message = f"{type(self).__name__} {self.program} "
            self.obs_id = await self.get_obs_id()
            if self.obs_id is not None:
                self.checkpoint_message += f"{self.obs_id}"
            if self.reason is not None:
                self.checkpoint_message += f" {self.reason}"

    async def get_obs_id(self) -> str | None:
        """Get obs id from camera obs id server.

        Returns
        -------
        `str` or None
            Id generated from camera server.
        """
        project, ticket_id_str = self.program.split("-", maxsplit=1)
        site = os.environ.get("LSST_SITE")
        if site is None or site not in IMAGE_SERVER_URL or project != "BLOCK":
            message = (
                "LSST_SITE environment variable not defined"
                if site is None
                else f"No image server url for {site=}."
                if site not in IMAGE_SERVER_URL
                else f"Ids are only generated for BLOCK programs, got {self.program}."
            )
            self.log.warning(f"Not generating obs id. {message}")
            return None

        try:
            ticket_id = abs(int(ticket_id_str))
            image_server_url = IMAGE_SERVER_URL[site]
            image_server_client = utils.ImageNameServiceClient(
                image_server_url, ticket_id, "Block"
            )
            _, data = await image_server_client.get_next_obs_id(num_images=1)
            return data[0]
        except ValueError:
            raise RuntimeError(
                f"Invalid BLOCK id. Got {ticket_id_str}, expected an integer type id."
            )
        except Exception:
            self.log.exception(f"Failed to generate obs id for {self.program}.")
            return None

    @contextlib.asynccontextmanager
    async def program_reason(self):
        """Context manager to publish appropriate checkpoints with program
        and reason.
        """
        try:
            if self.checkpoint_message is not None:
                await self.checkpoint(f"{self.checkpoint_message}: Start")
            yield
        finally:
            if self.checkpoint_message is not None:
                await self.checkpoint(f"{self.checkpoint_message}: Done")

            await self.save_test_case()

    @contextlib.asynccontextmanager
    async def test_case_step(self, comment: str | None = None) -> None:
        """Context manager to handle test case steps."""

        if self.step_counter is None:
            yield dict()
        else:
            step_result = dict(
                id=next(self.step_counter),
                executionTime=datetime.now().isoformat(),
            )
            if comment is not None:
                step_result["comment"] = comment
            try:
                yield step_result
            except Exception:
                step_result["status"] = "FAILED"
                self.step_results.append(step_result)
                raise
            else:
                step_result["status"] = "PASSED"
                self.step_results.append(step_result)

    async def save_test_case(self) -> None:
        """Save test case to the LFA."""

        if self.test_case is None:
            return

        if len(self.step_results) == 0:
            self.log.warning(
                "No test case step registered, no test case results to store. Skipping."
            )
            return

        self.log.info("Saving test case metadata to LFA.")

        test_case_payload = json.dumps(
            dict(
                projectId=self.test_case.get("project", "LVV"),
                issueId=self.test_case["name"],
                executionId=self.test_case["execution"],
                versionId=self.test_case["version"],
                stepResults=self.step_results,
            )
        ).encode()

        test_case_output = io.BytesIO()
        byte_size = test_case_output.write(test_case_payload)
        test_case_output.seek(0)

        s3bucket = get_s3_bucket()

        key = s3bucket.make_key(
            salname=self.salinfo.name,
            salindexname=self.salinfo.index,
            generator=self.test_case["name"],
            date=utils.astropy_time_from_tai_unix(utils.current_tai()),
            other=self.obs_id,
            suffix=".json",
        )

        await s3bucket.upload(fileobj=test_case_output, key=key)

        url = f"{s3bucket.service_resource.meta.client.meta.endpoint_url}/{s3bucket.name}/{key}"

        md5 = hashlib.md5()
        md5.update(test_case_payload)

        await self.evt_largeFileObjectAvailable.set_write(
            id=self.obs_id,
            url=url,
            generator=self.test_case["name"],
            mimeType="JSON",
            byteSize=byte_size,
            checkSum=md5.hexdigest(),
            version=1,
        )

    async def run(self):
        """Override base script run to encapsulate execution with appropriate
        checkpoints.
        """
        async with self.program_reason():
            await self.run_block()

    @abc.abstractmethod
    async def run_block(self):
        raise NotImplementedError()
