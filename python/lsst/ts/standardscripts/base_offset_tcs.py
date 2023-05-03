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

__all__ = ["BaseOffsetTCS"]

import abc

import yaml
from lsst.ts import salobj


class BaseOffsetTCS(salobj.BaseScript, metaclass=abc.ABCMeta):
    """Base TCS offset script.

    Parameters
    ----------
    index : `int`
        Index of Script SAL component.

    Notes
    -----

    This class requires one of the following properties ["offset_azel",
    "offset_radec", "offset_xy", "offset_rot", "reset_offsets"] to be provided
    in the yaml in order to be configured. Providing more than one of the above
    properties will result in a Validation Error and the script will fail in
    the Configuration State.

    """

    def __init__(self, index, descr):
        super().__init__(index=index, descr=descr)

        self.config = None

    @property
    @abc.abstractmethod
    def tcs(self):
        raise NotImplementedError()

    @classmethod
    def get_schema(cls):
        schema_yaml = """
            $schema: http://json-schema.org/draft-07/schema#
            $id: https://github.com/lsst-ts/ts_standardscripts/auxtel/offset_atcs.yaml
            title: OffsetATCS v1
            description: Configuration for OffsetATCS Script.
            type: object
            properties:
              offset_azel:
                type: object
                description: Offset in local AzEl coordinates.
                properties:
                    az:
                        description: Offset in azimuth (arcsec).
                        type: number
                    el:
                        description: Offset in elevation (arcsec).
                        type: number
                required: ["az","el"]
              offset_radec:
                type: object
                description: Offset telescope in RA and Dec.
                properties:
                    ra:
                        description: Offset in ra (arcsec).
                        type: number
                    dec:
                        description: Offset in dec (arcsec).
                        type: number
                required: ["ra","dec"]
              offset_xy:
                type: object
                description: Offset in the detector X/Y plane.
                properties:
                    x:
                        description: Offset in camera x-axis (arcsec).
                        type: number
                    y:
                        description: Offset in camera y-axis (arcsec).
                        type: number
                required: ["x","y"]
              offset_rot:
                type: object
                description: Offset rotator angle.
                properties:
                    rot:
                        description: Offset rotataor (degrees).
                        type: number
                required: ["rot"]
              reset_offsets:
                type: object
                description: Reset offsets
                properties:
                    reset_absorbed:
                        description: Reset absorbed offset? If unsure, set True
                        type: boolean
                    reset_non_absorbed:
                        description: Reset non-absorbed offset? If unsure, set True
                        type: boolean
                required: ["reset_absorbed","reset_non_absorbed"]
              relative:
                description: If `True` (default) offset is applied relative to the current
                    position, if `False` offset replaces any existing offsets.
                type: boolean
                default: True
              absorb:
                description: If `True`, offset should be absorbed and persisted between
                    slews.
                type: boolean
                default: False
            additionalProperties: false
            oneOf:
                - required: ["offset_azel"]
                - required: ["offset_radec"]
                - required: ["offset_xy"]
                - required: ["offset_rot"]
                - required: ["reset_offsets"]
        """
        return yaml.safe_load(schema_yaml)

    async def configure(self, config):
        """Configure script.

        Parameters
        ----------
        config : `types.SimpleNamespace`
            Script configuration, as defined by `schema`.
        """

        self.offset_azel = getattr(config, "offset_azel", None)
        self.offset_radec = getattr(config, "offset_radec", None)
        self.offset_xy = getattr(config, "offset_xy", None)
        self.offset_rot = getattr(config, "offset_rot", None)
        self.reset_offsets = getattr(config, "reset_offsets", None)

        self.relative = config.relative
        self.absorb = config.absorb

    def set_metadata(self, metadata):
        metadata.duration = 10

    async def assert_feasibility(self) -> None:
        """Verify that the telescope is in a feasible state to
        execute the script.
        """

        await self.tcs.assert_all_enabled()

    async def run(self):
        await self.assert_feasibility()

        if self.offset_azel is not None:
            await self.tcs.offset_azel(
                az=self.offset_azel["az"],
                el=self.offset_azel["el"],
                relative=self.relative,
                absorb=self.absorb,
            )

        if self.offset_radec is not None:
            await self.tcs.offset_radec(
                ra=self.offset_radec["ra"],
                dec=self.offset_radec["dec"],
                relative=self.relative,
                absorb=self.absorb,
            )

        if self.offset_xy is not None:
            await self.tcs.offset_xy(
                x=self.offset_xy["x"],
                y=self.offset_xy["y"],
                relative=self.relative,
                absorb=self.absorb,
            )

        if self.offset_rot is not None:
            await self.tcs.offset_rot(
                rot=self.offset_rot["rot"],
            )

        if self.reset_offsets is not None:
            await self.tcs.reset_offsets(
                absorbed=self.reset_offsets["reset_absorbed"],
                non_absorbed=self.reset_offsets["reset_non_absorbed"],
            )
