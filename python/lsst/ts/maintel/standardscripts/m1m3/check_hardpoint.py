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

__all__ = ["CheckHardpoint"]

import asyncio
import warnings

import yaml
from lsst.ts.observatory.control.maintel.mtcs import MTCS
from lsst.ts.standardscripts.base_block_script import BaseBlockScript

try:
    from lsst.ts.idl.enums.MTM1M3 import DetailedState
except ImportError:
    warnings.warn(
        "Could not import MTM1M3 from lsst.ts.idl; importing from lsst.ts.xml",
        UserWarning,
    )
    from lsst.ts.xml.enums.MTM1M3 import DetailedStates as DetailedState


class CheckHardpoint(BaseBlockScript):
    """Check M1M3 Individual hardpoint breakaway.

    Parameters
    ----------
    index : `int`
        Index of Script SAL component.

    Notes
    -----
    **Checkpoints**

    - "Testing hardpoint {id}.": Check hardpoint.
    - "Hardpoint breakaway check complete.": Check complete.

    """

    def __init__(self, index, add_remotes: bool = True):
        super().__init__(index=index, descr="Check M1M3 Hardpoint")

        self.mtcs = None

        self.timeout_check = 60
        self.timeout_std = 60

        self.hardpoints = range(1, 7)

    @classmethod
    def get_schema(cls):
        url = "https://github.com/lsst-ts/"
        path = (
            "ts_externalscripts/blob/main/python/lsst/ts/standardscripts/"
            "maintel/m1m3/check_hardpoint.py"
        )
        schema_yaml = f"""
        $schema: http://json-schema.org/draft-07/schema#
        $id: {url}{path}
        title: CheckHardpoint v1
        description: Configuration for Maintel check hardpoint breakaway test SAL Script.
        type: object
        properties:
            hardpoints:
                description: Hardpoints to run the breakway test.
                oneOf:
                  - type: array
                    minItems: 1
                    items:
                      type: number
                      minimum: 1
                      maximum: 6
                  - type: string
                    enum: ["all"]
                default: "all"
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
        self.hardpoints = (
            range(1, 7) if config.hardpoints == "all" else config.hardpoints
        )

        if self.mtcs is None:
            self.mtcs = MTCS(self.domain, log=self.log)
            await self.mtcs.start_task

        for comp in self.mtcs.components_attr:
            if comp != "mtm1m3":
                setattr(self.mtcs.check, comp, False)

        await super().configure(config=config)

    def set_metadata(self, metadata):
        metadata.duration = self.timeout_check * 2 + self.timeout_std

    async def run_individual_test(self, idx, hp):
        await self.checkpoint(f"Testing hardpoint {hp}.")
        await self.mtcs.run_m1m3_hard_point_test(hp=hp)
        self.log.info(f"Tests complete: {idx + 1}/{len(self.hardpoints)}")

    async def run_block(self):
        # Check that the MTCS is in the right state
        await asyncio.gather(
            self.mtcs.assert_all_enabled(),
            self.mtcs.assert_liveliness(),
            self.mtcs.assert_m1m3_detailed_state(
                {DetailedState.PARKED, DetailedState.PARKEDENGINEERING}
            ),
        )

        await self.mtcs.enter_m1m3_engineering_mode()

        tasks = [
            self.run_individual_test(idx, hp)
            for (idx, hp) in enumerate(self.hardpoints)
        ]
        return_values = await asyncio.gather(*tasks, return_exceptions=True)
        exceptions = [
            (hp, value)
            for (hp, value) in zip(self.hardpoints, return_values)
            if isinstance(value, Exception)
        ]

        if exceptions:
            err_message = f"{len(exceptions)} out of {len(self.hardpoints)} hard point tests failed.\n"
            for hp, exception in exceptions:
                err_message += f"Hardpoint {hp} test failed with {exception!r}.\n"
            raise RuntimeError(err_message)

        await self.checkpoint("Hardpoint breakaway check complete.")

    async def cleanup(self):
        self.log.info(
            f"Terminating with state={self.state.state}: exit engineering mode."
        )
        await self.mtcs.exit_m1m3_engineering_mode()
