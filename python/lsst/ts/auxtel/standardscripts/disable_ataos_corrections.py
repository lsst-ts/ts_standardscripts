# This file is part of ts_auxtel_standardscripts
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

__all__ = ["DisableATAOSCorrections"]

import yaml
from lsst.ts import salobj
from lsst.ts.observatory.control.auxtel.atcs import ATCS, ATCSUsages


class DisableATAOSCorrections(salobj.BaseScript):
    """Disable ATAOS corrections as a stand alone operation.

    Parameters
    ----------
    index : `int`
        Index of Script SAL component.

    """

    def __init__(self, index):
        super().__init__(index=index, descr="Disable ATAOS corrections")
        self.atcs = None

    @classmethod
    def get_schema(cls):
        schema_yaml = """
            $schema: http://json-schema.org/draft-07/schema#
            $id: https://github.com/lsst-ts/ts_standardscripts/auxtel/enable_latiss.yaml
            title: DisableATAOSCorrections v1
            description: Configuration for DisableATAOSCorrections
            type: object
            properties:
                ignore_fail:
                    description: Should it be ignored if the disable operation fails?
                        If False and the attempt to disable ATAOS corrections fails, an exception is raised.
                        If True and the attempt to disable ATAOS corrections fails, no exception is raised.
                        If disabling ATAOS corrections is successful, the parameter has no effect.
                    type: boolean
                    default: true

                ignore:
                    description: >-
                        CSCs from the group to ignore. Name must match those in
                        self.group.components, e.g.; atmcs.
                    type: array
                    items:
                        type: string

            additionalProperties: false
        """
        return yaml.safe_load(schema_yaml)

    async def configure(self, config):
        self.config = config
        self.ignore_fail = config.ignore_fail

        if self.atcs is None:
            self.atcs = ATCS(
                domain=self.domain, intended_usage=ATCSUsages.All, log=self.log
            )
            await self.atcs.start_task

        if hasattr(self.config, "ignore"):
            for comp in self.config.ignore:
                if comp not in self.atcs.components_attr:
                    self.log.warning(
                        f"Component {comp} not in CSC Group. "
                        f"Must be one of {self.atcs.components_attr}. Ignoring."
                    )
                else:
                    self.log.debug(f"Ignoring component {comp}.")
                    setattr(self.atcs.check, comp, False)

    def set_metadata(self, metadata):
        pass

    async def run(self):
        """Run script."""
        await self.atcs.assert_all_enabled()
        await self.atcs.disable_ataos_corrections(ignore_fail=self.ignore_fail)
