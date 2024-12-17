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

__all__ = ["TakeStutteredLatiss"]

import yaml
from lsst.ts.observatory.control.auxtel import LATISS, LATISSUsages
from lsst.ts.standardscripts.base_take_stuttered import BaseTakeStuttered


class TakeStutteredLatiss(BaseTakeStuttered):
    """Take a series of stuttered images with LATISS.

    Parameters
    ----------
    index : `int`
        SAL index of this Script
    """

    def __init__(self, index):
        super().__init__(index=index, descr="Take stuttered images with LATISS")

        self._latiss = LATISS(
            self.domain, intended_usage=LATISSUsages.TakeImageFull, log=self.log
        )

    @property
    def camera(self):
        return self._latiss

    @classmethod
    def get_schema(cls):
        schema_yaml = """
            $schema: http://json-schema.org/draft-07/schema#
            $id: https://github.com/lsst-ts/ts_standardscripts/auxtel/latiss_take_stuttered.py
            title: TakeStutteredLatiss v1
            description: Configuration for TakeStutteredLatiss.
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
            required: [exp_time, n_images]
            additionalProperties: false
        """
        schema_dict = yaml.safe_load(schema_yaml)

        base_schema_dict = super(TakeStutteredLatiss, cls).get_schema()

        for prop in base_schema_dict["properties"]:
            schema_dict["properties"][prop] = base_schema_dict["properties"][prop]

        return schema_dict

    def get_instrument_configuration(self):
        return dict(
            filter=self.config.filter,
            grating=self.config.grating,
            linear_stage=self.config.linear_stage,
        )
