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

__all__ = ["EnableLATISS"]

import yaml

from lsst.ts import salobj
from lsst.ts.observatory.control.auxtel.latiss import LATISS, LATISSUsages


class EnableLATISS(salobj.BaseScript):
    """Enable all LATISS components.

    Parameters
    ----------
    index : `int`
        Index of Script SAL component.

    Notes
    -----
    **Checkpoints**

    **Details**

    """

    def __init__(self, index):

        super().__init__(index=index, descr="Enable LATISS.")

        self.config = None

        self.latiss = LATISS(self.domain, intended_usage=LATISSUsages.StateTransition)

    @classmethod
    def get_schema(cls):
        schema_yaml = """
            $schema: http://json-schema.org/draft-07/schema#
            $id: https://github.com/lsst-ts/ts_standardscripts/auxtel/enable_latiss.yaml
            title: EnableLATISS v1
            description: Configuration for EnableLATISS
            type: object
            properties:
                atcamera:
                    description: Configuration for the ATCamera component.
                    anyOf:
                      - type: string
                      - type: "null"
                    default: null
                atspectrograph:
                    description: Configuration for the ATSpectrograph component.
                    anyOf:
                      - type: string
                      - type: "null"
                    default: null
                atheaderservice:
                    description: Configuration for the ATHeaderService component.
                    anyOf:
                      - type: string
                      - type: "null"
                    default: null
                atarchiver:
                    description: Configuration for the ATArchiver component.
                    anyOf:
                      - type: string
                      - type: "null"
                    default: null
            additionalProperties: false
        """
        return yaml.safe_load(schema_yaml)

    async def configure(self, config):
        self.config = config

    def set_metadata(self, metadata):
        metadata.duration = 60.0

    async def run(self):
        settings = (
            dict(
                [(comp, getattr(self.config, comp)) for comp in self.latiss.components]
            )
            if self.config is not None
            else None
        )
        await self.latiss.enable(settings=settings)
