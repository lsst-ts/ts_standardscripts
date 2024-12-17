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

__all__ = ["TakeImageComCam"]

import yaml
from lsst.ts.observatory.control.maintel.comcam import ComCam, ComCamUsages
from lsst.ts.observatory.control.maintel.mtcs import MTCS, MTCSUsages
from lsst.ts.standardscripts.base_take_image import BaseTakeImage


class TakeImageComCam(BaseTakeImage):
    """Take images with ComCam.

    Parameters
    ----------
    index : `int`
        Index of Script SAL component.

    Notes
    -----
    **Checkpoints**

    * exposure {n} of {m}: before sending the CCCamera ``takeImages`` command

    """

    def __init__(self, index):
        super().__init__(index=index, descr="Take images with ComCam.")

        self.config = None

        self.mtcs = MTCS(self.domain, log=self.log, intended_usage=MTCSUsages.Slew)

        self._comcam = ComCam(
            self.domain,
            intended_usage=ComCamUsages.TakeImage,
            log=self.log,
            tcs_ready_to_take_data=self.mtcs.ready_to_take_data,
        )

        self.instrument_name = "LSSTComCam"

    @property
    def camera(self):
        return self._comcam

    @classmethod
    def get_schema(cls):
        schema_yaml = """
            $schema: http://json-schema.org/draft-07/schema#
            $id: https://github.com/lsst-ts/ts_standardscripts/maintel/ComCamTakeImage.yaml
            title: ComCamTakeImage v1
            description: Configuration for ComCamTakeImage.
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
              sim:
                description: Is ComCam in simulation mode? This mode is used for tests.
                type: boolean
                default: false
            additionalProperties: false
        """
        schema_dict = yaml.safe_load(schema_yaml)

        base_schema_dict = super(TakeImageComCam, cls).get_schema()

        for prop in base_schema_dict["properties"]:
            schema_dict["properties"][prop] = base_schema_dict["properties"][prop]

        return schema_dict

    def get_instrument_name(self):
        if self.config is not None and self.config.sim:
            return self.instrument_name + "Sim"

        return self.instrument_name

    def get_instrument_configuration(self):
        return dict(filter=self.config.filter)
