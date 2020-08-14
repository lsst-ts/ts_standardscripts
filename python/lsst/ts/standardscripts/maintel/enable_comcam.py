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

__all__ = ["EnableComCam"]

import yaml

from ..enable_group import EnableGroup
from lsst.ts.observatory.control.maintel.comcam import ComCam, ComCamUsages


class EnableComCam(EnableGroup):
    """Enable all ComCam components.

    The Script configuration only accepts settings values for the CSCs that
    are configurable.

    The following CSCs will be enabled:

        - CCCamera
        - CCHeaderService: not configurable
        - CCArchiver

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
        super().__init__(index=index, descr="Enable ComCam.")

        self.config = None

        self._comcam = ComCam(
            self.domain, intended_usage=ComCamUsages.StateTransition, log=self.log
        )

    @property
    def group(self):
        return self._comcam

    @classmethod
    def get_schema(cls):
        schema_yaml = """
            $schema: http://json-schema.org/draft-07/schema#
            $id: https://github.com/lsst-ts/ts_standardscripts/maintel/enable_mtcs.yaml
            title: EnableComCam v1
            description: Configuration for EnableComCam
            type: object
            properties:
                cccamera:
                    description: Configuration for the CCCamera component.
                    anyOf:
                      - type: string
                      - type: "null"
                    default: null
                ccarchiver:
                    description: Configuration for the CCArchiver component.
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
