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
import os

import yaml
from lsst.ts import salobj, utils

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
        self.checkpoint_message = None

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
                    Program this script is related to. If this has the format
                    of a block program (e.g. BLOCK-NNNN, where N is an
                    integer value), it will be used to generate an ID for the
                    script execution. A warning message is issued if this is
                    provided in with any different format.
            reason:
                type: string
                description: Reason for executing this script.
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
        if self.program is not None:
            self.checkpoint_message = f"{type(self).__name__} {self.program} "
            obs_id = await self.get_obs_id()
            if obs_id is not None:
                self.checkpoint_message += f"{obs_id}"
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

    async def run(self):
        """Override base script run to encapsulate execution with appropriate
        checkpoints.
        """
        async with self.program_reason():
            await self.run_block()

    @abc.abstractmethod
    async def run_block(self):
        raise NotImplementedError()
