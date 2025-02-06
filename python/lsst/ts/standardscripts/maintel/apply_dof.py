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
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

__all__ = ["ApplyDOF"]

import typing

import numpy as np
import yaml
from lsst.ts import salobj
from lsst.ts.observatory.control.maintel.mtcs import MTCS
from lsst.ts.observatory.control.utils.enums import DOFName


class ApplyDOF(salobj.BaseScript):
    """Apply a DOF to the main telescope, either bending
    mode or hexapod offset.

    Parameters
    ----------
    index : `int`
        Index of Script SAL component.

    Notes
    -----
    **Checkpoints**
    "Applying DOF offset..." - The DOF offset is being applied.

    """

    def __init__(self, index) -> None:
        super().__init__(
            index=index,
            descr="Apply an offset to the degrees of freedom of the main telescope.",
        )

        # Create the MTCS object
        self.mtcs = None

        # Create the DOF vector
        self.dofs = np.zeros(len(DOFName))

    async def configure_tcs(self) -> None:
        """Handle creating MTCS object and waiting for remote to start."""
        if self.mtcs is None:
            self.log.debug("Creating MTCS.")
            self.mtcs = MTCS(
                domain=self.domain,
                log=self.log,
            )
            await self.mtcs.start_task
        else:
            self.log.debug("MTCS already defined, skipping.")

    @classmethod
    def get_schema(cls) -> typing.Dict[str, typing.Any]:
        schema_yaml = """
            $schema: http://json-schema.org/draft-07/schema#
            $id: https://github.com/lsst-ts/ts_standardscripts/maintel/ApplyDOF.yaml
            title: ApplyDOF v1
            description: Configuration for ApplyDOF Script.
            type: object
            properties:
              dofs:
                type: array
                description: >-
                  Defines a 50-dimensional vector for all DOFs, combining M2,
                  Camera, M1M3, and M2 bending modes. This overrides individual DOF inputs.
                  First 5 elements for M2, next 5 for Camera, next 20 for M1M3 bending modes,
                  last 20 for M2 bending modes. Units: microns or arcsec.
                items:
                  type: number
                minItems: 50
                maxItems: 50
              M2_dz:
                  type: number
                  description: >-
                    Defines the offset applied to the M2 hexapod in the z direction.
                    Units in um.
                  default: 0.0
              M2_dx:
                  type: number
                  description: >-
                    Defines the offset applied to the M2 hexapod in the x direction.
                    Units in um.
                  default: 0.0
              M2_dy:
                  type: number
                  description: >-
                    Defines the offset applied to the M2 hexapod in the y direction.
                    Units in um.
                  default: 0.0
              M2_rx:
                  type: number
                  description: >-
                    Defines the offset applied to the M2 hexapod in rx.
                    Units in arcsec.
                  default: 0.0
              M2_ry:
                  type: number
                  description: >-
                    Defines the offset applied to the M2 hexapod in ry.
                    Units in arcsec.
                  default: 0.0
              Cam_dz:
                  type: number
                  description: >-
                    Defines the offset applied to the Camera hexapod in
                    the z direction. Units in um.
                  default: 0.0
              Cam_dx:
                  type: number
                  description: >-
                    Defines the offset applied to the Camera hexapod
                    in the x direction. Units in um.
                  default: 0.0
              Cam_dy:
                  type: number
                  description: >-
                    Defines the offset applied to the Camera hexapod in
                    the y direction. Units in um.
                  default: 0.0
              Cam_rx:
                  type: number
                  description: >-
                    Defines the offset applied to the Camera hexapod in rx.
                    Units in arcsec.
                  default: 0.0
              Cam_ry:
                  type: number
                  description: >-
                    Defines the offset applied to the Camera hexapod in ry.
                    Units in arcsec.
                  default: 0.0
              M1M3_B1:
                  type: number
                  description: >-
                    Defines the offset applied to the M1M3 bending mode 1.
                    Units in um.
                  default: 0.0
              M1M3_B2:
                  type: number
                  description: >-
                    Defines the offset applied to the M1M3 bending mode 2.
                    Units in um.
                  default: 0.0
              M1M3_B3:
                  type: number
                  description: >-
                    Defines the offset applied to the M1M3 bending mode 3.
                    Units in um.
                  default: 0.0
              M1M3_B4:
                  type: number
                  description: >-
                    Defines the offset applied to the M1M3 bending mode 4.
                    Units in um.
                  default: 0.0
              M1M3_B5:
                  type: number
                  description: >-
                    Defines the offset applied to the M1M3 bending mode 5.
                    Units in um.
                  default: 0.0
              M1M3_B6:
                  type: number
                  description: >-
                    Defines the offset applied to the M1M3 bending mode 6.
                    Units in um.
                  default: 0.0
              M1M3_B7:
                  type: number
                  description: >-
                    Defines the offset applied to the M1M3 bending mode 7.
                    Units in um.
                  default: 0.0
              M1M3_B8:
                  type: number
                  description: >-
                    Defines the offset applied to the M1M3 bending mode 8.
                    Units in um.
                  default: 0.0
              M1M3_B9:
                  type: number
                  description: >-
                    Defines the offset applied to the M1M3 bending mode 9.
                    Units in um.
                  default: 0.0
              M1M3_B10:
                  type: number
                  description: >-
                    Defines the offset applied to the M1M3 bending mode 10.
                    Units in um.
                  default: 0.0
              M1M3_B11:
                  type: number
                  description: >-
                    Defines the offset applied to the M1M3 bending mode 11.
                    Units in um.
                  default: 0.0
              M1M3_B12:
                  type: number
                  description: >-
                    Defines the offset applied to the M1M3 bending mode 12.
                    Units in um.
                  default: 0.0
              M1M3_B13:
                  type: number
                  description: >-
                    Defines the offset applied to the M1M3 bending mode 13.
                    Units in um.
                  default: 0.0
              M1M3_B14:
                  type: number
                  description: >-
                    Defines the offset applied to the M1M3 bending mode 14.
                    Units in um.
                  default: 0.0
              M1M3_B15:
                  type: number
                  description: >-
                    Defines the offset applied to the M1M3 bending mode 15.
                    Units in um.
                  default: 0.0
              M1M3_B16:
                  type: number
                  description: >-
                    Defines the offset applied to the M1M3 bending mode 16.
                    Units in um.
                  default: 0.0
              M1M3_B17:
                  type: number
                  description: >-
                    Defines the offset applied to the M1M3 bending mode 17.
                    Units in um.
                  default: 0.0
              M1M3_B18:
                  type: number
                  description: >-
                    Defines the offset applied to the M1M3 bending mode 18.
                    Units in um.
                  default: 0.0
              M1M3_B19:
                  type: number
                  description: >-
                    Defines the offset applied to the M1M3 bending mode 19.
                    Units in um.
                  default: 0.0
              M1M3_B20:
                  type: number
                  description: >-
                    Defines the offset applied to the M1M3 bending mode 20.
                    Units in um.
                  default: 0.0
              M2_B1:
                  type: number
                  description: >-
                    Defines the offset applied to the M2 bending mode 1.
                    Units in um.
                  default: 0.0
              M2_B2:
                  type: number
                  description: >-
                    Defines the offset applied to the M2 bending mode 2.
                    Units in um.
                  default: 0.0
              M2_B3:
                  type: number
                  description: >-
                    Defines the offset applied to the M2 bending mode 3.
                    Units in um.
                  default: 0.0
              M2_B4:
                  type: number
                  description: >-
                    Defines the offset applied to the M2 bending mode 4.
                    Units in um.
                  default: 0.0
              M2_B5:
                  type: number
                  description: >-
                    Defines the offset applied to the M2 bending mode 5.
                    Units in um.
                  default: 0.0
              M2_B6:
                  type: number
                  description: >-
                    Defines the offset applied to the M2 bending mode 6.
                    Units in um.
                  default: 0.0
              M2_B7:
                  type: number
                  description: >-
                    Defines the offset applied to the M2 bending mode 7.
                    Units in um.
                  default: 0.0
              M2_B8:
                  type: number
                  description: >-
                    Defines the offset applied to the M2 bending mode 8.
                    Units in um.
                  default: 0.0
              M2_B9:
                  type: number
                  description: >-
                    Defines the offset applied to the M2 bending mode 9.
                    Units in um.
                  default: 0.0
              M2_B10:
                  type: number
                  description: >-
                    Defines the offset applied to the M2 bending mode 10.
                    Units in um.
                  default: 0.0
              M2_B11:
                  type: number
                  description: >-
                    Defines the offset applied to the M2 bending mode 11.
                    Units in um.
                  default: 0.0
              M2_B12:
                  type: number
                  description: >-
                    Defines the offset applied to the M2 bending mode 12.
                    Units in um.
                  default: 0.0
              M2_B13:
                  type: number
                  description: >-
                    Defines the offset applied to the M2 bending mode 13.
                    Units in um.
                  default: 0.0
              M2_B14:
                  type: number
                  description: >-
                    Defines the offset applied to the M2 bending mode 14.
                    Units in um.
                  default: 0.0
              M2_B15:
                  type: number
                  description: >-
                    Defines the offset applied to the M2 bending mode 15.
                    Units in um.
                  default: 0.0
              M2_B16:
                  type: number
                  description: >-
                    Defines the offset applied to the M2 bending mode 16.
                    Units in um.
                  default: 0.0
              M2_B17:
                  type: number
                  description: >-
                    Defines the offset applied to the M2 bending mode 17.
                    Units in um.
                  default: 0.0
              M2_B18:
                  type: number
                  description: >-
                    Defines the offset applied to the M2 bending mode 18.
                    Units in um.
                  default: 0.0
              M2_B19:
                  type: number
                  description: >-
                    Defines the offset applied to the M2 bending mode 19.
                    Units in um.
                  default: 0.0
              M2_B20:
                  type: number
                  description: >-
                    Defines the offset applied to the M2 bending mode 20.
                    Units in um.
                  default: 0.0
              ignore:
                  description: >-
                      CSCs from the group to ignore in status check. Name must
                      match those in self.group.components, e.g.; hexapod_1.
                  type: array
                  items:
                      type: string
            additionalProperties: false
        """
        return yaml.safe_load(schema_yaml)

    async def configure(self, config) -> None:
        """Configure script.

        Parameters
        ----------
        config : `types.SimpleNamespace`
            Script configuration, as defined by `schema`.
        """

        # Configure tcs and camera
        await self.configure_tcs()

        if hasattr(config, "dofs"):
            self.dofs = config.dofs
        else:
            # Loop through properties and assign their values to the vector
            for key, value in vars(config).items():
                if hasattr(DOFName, key):
                    self.dofs[getattr(DOFName, key)] = value
                else:
                    self.log.warning(f"{key} is not a DOFName, ignoring.")

        if hasattr(config, "ignore"):
            self.mtcs.disable_checks_for_components(components=config.ignore)

    def set_metadata(self, metadata) -> None:
        """Set script metadata.

        Parameters
        ----------
        metadata : `lsst.ts.salobj.base.ScriptMetadata`
            Script metadata.
        """
        metadata.duration = 10

    async def assert_feasibility(self) -> None:
        """Verify that the telescope is in a feasible state to
        execute the script.
        """

        await self.mtcs.assert_all_enabled()

    async def run(self) -> None:
        """Run script."""
        # Assert feasibility
        await self.assert_feasibility()

        await self.checkpoint("Applying DOF offset...")
        offset_dof_data = self.mtcs.rem.mtaos.cmd_offsetDOF.DataType()
        for i, dof_offset in enumerate(self.dofs):
            offset_dof_data.value[i] = dof_offset
        await self.mtcs.rem.mtaos.cmd_offsetDOF.start(data=offset_dof_data)
