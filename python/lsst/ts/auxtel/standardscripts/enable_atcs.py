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
# along with this program. If not, see <https://www.gnu.org/licenses/>.

__all__ = ["EnableATTCS"]

import yaml
from lsst.ts.observatory.control.auxtel.atcs import ATCS, ATCSUsages
from lsst.ts.standardscripts.enable_group import EnableGroup


class EnableATTCS(EnableGroup):
    """Enable all ATCS components.

    The Script configuration only accepts settings values for the CSCs that
    are configurable.

    The following CSCs will be enabled:

        - ATMCS: not configurable
        - ATPtg: not configurable
        - ATAOS
        - ATPneumatics: not configurable
        - ATHexapod
        - ATDome
        - ATDomeTrajectory

    Parameters
    ----------
    index : `int`
        Index of Script SAL component.

    Notes
    -----
    **Checkpoints**

    None

    """

    def __init__(self, index):
        super().__init__(index=index, descr="Enable ATCS.")

        self.config = None

        self._attcs = ATCS(
            self.domain, intended_usage=ATCSUsages.StateTransition, log=self.log
        )

    @property
    def group(self):
        return self._attcs

    @staticmethod
    def components():
        """Return list of components name as appeared in
        `self.group.components`.

        Returns
        -------
        components : `list` of `str`.

        """
        return set(
            [
                "atmcs",
                "atptg",
                "ataos",
                "atpneumatics",
                "athexapod",
                "atdome",
                "atdometrajectory",
            ]
        )

    @classmethod
    def get_schema(cls):
        schema_yaml = f"""
            $schema: http://json-schema.org/draft-07/schema#
            $id: https://github.com/lsst-ts/ts_standardscripts/auxtel/enable_atcs.yaml
            title: EnableATTCS v1
            description: Configuration for EnableATTCS. Only include those CSCs that are configurable.
            type: object
            properties:
                ataos:
                    description: Configuration for the ATAOS component.
                    anyOf:
                      - type: string
                      - type: "null"
                    default: null
                athexapod:
                    description: Configuration for the ATHexapod component.
                    anyOf:
                      - type: string
                      - type: "null"
                    default: null
                atdome:
                    description: Configuration for the ATHexapod component.
                    anyOf:
                      - type: string
                      - type: "null"
                    default: null
                atdometrajectory:
                    description: Configuration for the ATHexapod component.
                    anyOf:
                      - type: string
                      - type: "null"
                    default: null
                ignore:
                    description: >-
                        CSCs from the group to ignore. Name must match those in
                        self.group.components, e.g.; atdometrajectory.
                        Valid options are: {cls.components()}
                    type: array
                    items:
                        type: string
            additionalProperties: false
        """
        return yaml.safe_load(schema_yaml)
