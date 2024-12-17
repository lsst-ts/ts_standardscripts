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

__all__ = ["TakeImageLatiss"]

import yaml
from lsst.ts.observatory.control.auxtel import ATCS, LATISS, ATCSUsages, LATISSUsages
from lsst.ts.standardscripts.base_take_image import BaseTakeImage


class TakeImageLatiss(BaseTakeImage):
    """Take a series of images with the ATCamera with set exposure times.

    Parameters
    ----------
    index : `int`
        SAL index of this Script

    Notes
    -----
    **Checkpoints**

    * exposure {n} of {m}: before sending the ATCamera ``takeImages`` command

    """

    def __init__(self, index):
        super().__init__(index=index, descr="Take images with AT Camera")

        self.atcs = ATCS(self.domain, log=self.log, intended_usage=ATCSUsages.Slew)

        self._latiss = LATISS(
            self.domain,
            intended_usage=LATISSUsages.TakeImageFull,
            log=self.log,
            tcs_ready_to_take_data=self.atcs.ready_to_take_data,
        )

        self.instrument_name = "LATISS"

    @property
    def camera(self):
        return self._latiss

    @classmethod
    def get_schema(cls):
        schema_yaml = """
            $schema: http://json-schema.org/draft-07/schema#
            $id: https://github.com/lsst-ts/ts_standardscripts/auxtel/LatissTakeImage.yaml
            title: LatissTakeImage v2
            description: Configuration for LatissTakeImage.
            type: object
            properties:
              filter:
                description: Filter name or ID; if omitted the filter is not changed.
                anyOf:
                  - type: string
                  - type: integer
                    minimum: 1
                  - type: "null"
                default: null
              grating:
                description: Grating name; if omitted the grating is not changed.
                anyOf:
                  - type: string
                  - type: integer
                    minimum: 1
                  - type: "null"
                default: null
              linear_stage:
                description: Linear stage position; if omitted the linear stage is not moved.
                anyOf:
                  - type: number
                  - type: "null"
                default: null
            required: [image_type]
            additionalProperties: false
        """
        schema_dict = yaml.safe_load(schema_yaml)

        base_schema_dict = super(TakeImageLatiss, cls).get_schema()

        for prop in base_schema_dict["properties"]:
            schema_dict["properties"][prop] = base_schema_dict["properties"][prop]

        return schema_dict

    def get_instrument_name(self):
        return self.instrument_name

    def get_instrument_configuration(self):
        return dict(
            filter=self.config.filter,
            grating=self.config.grating,
            linear_stage=self.config.linear_stage,
        )

    def get_instrument_filter(self):
        """Get instrument filter configuration.

        Returns
        -------
        instrument_filter: `string`
        """
        filter = self.config.filter
        grating = self.config.grating
        return f"{filter}~{grating}"
