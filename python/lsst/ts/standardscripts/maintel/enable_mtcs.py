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

__all__ = ["EnableMTCS"]

import yaml

from ..enable_group import EnableGroup
from lsst.ts.observatory.control.maintel.mtcs import MTCS, MTCSUsages


class EnableMTCS(EnableGroup):
    """Enable all MTCS components.

    The Script configuration only accepts settings values for the CSCs that
    are configurable.

    The following CSCs will be enabled:

        - NewMTMount
        - MTPtg: not configurable
        - MTAOS
        - MTM1M3
        - MTM2
        - Hexapod:1
        - Hexapod:2
        - Rotator: not configurable
        - Dome
        - MTDomeTrajectory

    Parameters
    ----------
    index : `int`
        Index of Script SAL component.

    Notes
    -----
    **Checkpoints**

    **Details**

    """

    __test__ = False  # stop pytest from warning that this is not a test

    def __init__(self, index):
        super().__init__(index=index, descr="Enable MTCS.")

        self.config = None

        self._mtcs = MTCS(
            self.domain, intended_usage=MTCSUsages.StateTransition, log=self.log
        )

    @property
    def group(self):
        return self._mtcs

    @classmethod
    def get_schema(cls):
        schema_yaml = """
            $schema: http://json-schema.org/draft-07/schema#
            $id: https://github.com/lsst-ts/ts_standardscripts/maintel/enable_mtcs.yaml
            title: EnableMTCS v1
            description: Configuration for EnableMTCS
            type: object
            properties:
                newmtmount:
                    description: Configuration for the NewMTMount component.
                    anyOf:
                      - type: string
                      - type: "null"
                    default: null
                mtaos:
                    description: Configuration for the ATAOS component.
                    anyOf:
                      - type: string
                      - type: "null"
                    default: null
                mtm1m3:
                    description: Configuration for the M1M3 component.
                    anyOf:
                      - type: string
                      - type: "null"
                    default: null
                mtm2:
                    description: Configuration for the MTM2 component.
                    anyOf:
                      - type: string
                      - type: "null"
                    default: null
                hexapod_1:
                    description: Configuration for the Camera Hexapod component.
                    anyOf:
                      - type: string
                      - type: "null"
                    default: null
                hexapod_2:
                    description: Configuration for the M2 Hexapod component.
                    anyOf:
                      - type: string
                      - type: "null"
                    default: null
                dome:
                    description: Configuration for the Dome component.
                    anyOf:
                      - type: string
                      - type: "null"
                    default: null
                mtdometrajectory:
                    description: Configuration for the MTDomeTrajectory component.
                    anyOf:
                      - type: string
                      - type: "null"
                    default: null
                ignore:
                    description: CSCs from the group to ignore.
                    type: array
                    items:
                        type: string
            additionalProperties: false
        """
        return yaml.safe_load(schema_yaml)
