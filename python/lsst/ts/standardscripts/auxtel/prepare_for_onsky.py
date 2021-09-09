# This file is part of ts_externalcripts
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

__all__ = ["PrepareForOnSky"]

import yaml

from lsst.ts import salobj
from lsst.ts.observatory.control.auxtel import (
    ATCS,
    LATISS,
    ATCSUsages,
    LATISSUsages,
)


class PrepareForOnSky(salobj.BaseScript):
    """Run ATTCS startup.

    Parameters
    ----------
    index : `int`
        Index of Script SAL component.

    Notes
    -----
    **Checkpoints**

    None

    """

    __test__ = False  # stop pytest from warning that this is not a test

    def __init__(self, index):
        super().__init__(index=index, descr="Run ATCS startup.")

        self.config = None

        self.attcs = ATCS(self.domain, intended_usage=ATCSUsages.StartUp, log=self.log)
        self.latiss = LATISS(
            self.domain, intended_usage=LATISSUsages.StateTransition, log=self.log
        )

    @classmethod
    def get_schema(cls):
        schema_yaml = """
            $schema: http://json-schema.org/draft-07/schema#
            $id: https://github.com/lsst-ts/ts_standardscripts/auxtel/prepare_for_onsky.yaml
            title: PrepareForOnSky v1
            description: Configuration for PrepareForOnSky
            type: object
            properties:
                atmcs:
                    description: Configuration for the ATMCS component.
                    anyOf:
                      - type: string
                      - type: "null"
                    default: null
                atptg:
                    description: Configuration for the ATPtg component.
                    anyOf:
                      - type: string
                      - type: "null"
                    default: null
                ataos:
                    description: Configuration for the ATAOS component.
                    anyOf:
                      - type: string
                      - type: "null"
                    default: null
                atpneumatics:
                    description: Configuration for the ATPneumatics component.
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
            additionalProperties: false
        """
        return yaml.safe_load(schema_yaml)

    async def configure(self, config):
        self.config = config

    def set_metadata(self, metadata):
        metadata.duration = 600.0

    async def run(self):
        settings = (
            dict(
                [
                    (comp, getattr(self.config, comp))
                    for comp in self.attcs.components_attr
                ]
            )
            if self.config is not None
            else None
        )
        await self.latiss.assert_all_enabled(
            message="All LATISS components need to be enabled to prepare for sky observations."
        )
        await self.attcs.prepare_for_onsky(settings=settings)
