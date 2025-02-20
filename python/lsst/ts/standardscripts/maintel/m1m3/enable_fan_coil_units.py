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
# along with this program. If not, see <https://www.gnu.org/licenses/>.

import yaml

from ..base_track_target import BaseTrackTarget

# M1M3 has 96 fan coil units
FAN_COIL_UNITS_COUNT = 96


class EnableFanCoilUnits(BaseTrackTarget):
    """Enable one or more fan coil units inside M1M3 subsystem.

    Parameters
    ----------
    index : `int`
        Index of Script SAL component.
    remote : `bool`
        Flag to indicate if the command should be executed remotely.
    """

    def __init__(self, index):
        super().__init__(
            index=index,
            descr="Enable one or more fan coil units inside M1M3 subsystem.",
        )

    @classmethod
    def get_schema(cls):
        m1m3_fcu_ids_str = ", ".join([str(i) for i in range(0, FAN_COIL_UNITS_COUNT)])
        url = "https://github.com/lsst-ts/"
        path = (
            "ts_standardscripts/blob/main/python/lsst/ts/standardscripts/"
            "maintel/m1m3/enable_fan_coil_units.py"
        )

        schema_yaml = f"""
        $schema: http://json-schema.org/draft-07/schema#
        $id: {url}{path}
        title: CheckAcutators v1
        description: >-
            Configuration for Maintel bump test SAL Script.
            You will need to either pass the power percentage or the RPM value.
            But, not both.
        type: object
        properties:
            fcus:
                description: Fan coil units to be enabled.
                oneOf:
                  - type: array
                    items:
                      type: number
                      enum: [{m1m3_fcu_ids_str}]
                    minItems: 1
                    uniqueItems: true
                    additionalItems: false
                  - type: string
                    enum: ["all"]
                default: "all"
            pwr:
                description : >-
                    Power percentage applied to the fan coil units.
                oneOf:
                    - type: array
                      items:
                        type: number
                        minimum: 0
                        maximum: 100
                      minItems: 1
                      uniqueItems: false
                      additionalItems: false
                    - type: number
                      minimum: 0
                      maximum: 100
            rpm:
                description : >-
                    Fan coil units speed in RPM.
                oneOf:
                    - type: array
                      items:
                        type: number
                        minimum: 0
                        maximum: 2550
                      minItems: 1
                      uniqueItems: false
                      additionalItems: false
                    - type: number
                      minimum: 0
                      maximum: 2550
        """
        return yaml.safe_load(schema_yaml)
