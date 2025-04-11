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
import warnings

import yaml
from lsst.ts import salobj, utils

IMAGE_SERVER_URL = dict(
    tucson="http://comcam-mcm.tu.lsst.org",
    base="http://lsstcam-mcm.ls.lsst.org",
    summit="http://ccs.lsst.org",
)


class BaseBlockScript(salobj.BaseScript, metaclass=abc.ABCMeta):
    """(Deprecated) Extend BaseScript to add support for executing blocks.

    This base class adds a default configuration with reason and program that
    can be provided when executing the script.

    Deprecated:
        This class is deprecated. BaseScript now supports block metadata
        directly.
        Future development should use BaseScript and its built-in block
        support.
    """

    def __init__(self, index: int, descr: str, help: str = "") -> None:
        warnings.warn(
            "BaseBlockScript is deprecated. salobj.BaseScript now supports"
            + " block metadata directly. "
            + "Future development should use salobj.BaseScript instead.",
            DeprecationWarning,
            stacklevel=2,
        )

        super().__init__(index, descr, help)

        self.program = None
        self.reason = None
        self.obs_id = None
        self.checkpoint_message = None

        self.test_case = None

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
        if self.test_case is not None:
            warnings.warn(
                "The test_case functionality in BaseBlockScript is deprecated and"
                + " will be removed.",
                DeprecationWarning,
                stacklevel=2,
            )
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

        Deprecated:
            This method no longer will generate obs_id values.
            The obs_id should now be provided by the script queue.

        Returns
        -------
        `str` or None
            Id generated from camera server.
        """
        warnings.warn(
            "The get_obs_id method in BaseBlockScript is deprecated. "
            "The obs_id should now be provided by the script queue.",
            DeprecationWarning,
            stacklevel=2,
        )

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
        """Context manager to handle test case steps.

        Deprecated:
            The test_case functionality is deprecated and will be removed.
        """
        warnings.warn(
            "The test_case_step method in BaseBlockScript is deprecated and"
            + " will be removed.",
            DeprecationWarning,
            stacklevel=2,
        )
        yield dict()

    async def save_test_case(self) -> None:
        """Save test case to the LFA.

        Deprecated:
            The test_case functionality is deprecated and will be removed.
        """
        warnings.warn(
            "The save_test_case method in BaseBlockScript is deprecated and"
            + " will be removed.",
            DeprecationWarning,
            stacklevel=2,
        )
        return

    async def run(self):
        """Override base script run to encapsulate execution with appropriate
        checkpoints.
        """
        async with self.program_reason():
            await self.run_block()

    @abc.abstractmethod
    async def run_block(self):
        raise NotImplementedError()
