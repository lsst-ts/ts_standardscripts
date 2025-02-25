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

__all__ = ["CalSysTakeData"]

import asyncio
import collections

import numpy as np
import yaml
from lsst.ts import salobj
from lsst.ts.idl.enums import ATMonochromator


def is_sequence(value):
    """Return True if value is a sequence that is not a `str` or `bytes`."""
    if isinstance(value, str) or isinstance(value, bytes):
        return False
    return isinstance(value, collections.abc.Sequence)


def as_array(value, dtype, nelt):
    """Return a scalar or sequence as a 1-d array of specified type and length.

    Parameters
    ----------
    value : ``any`` or `list` [``any``]
        Value to convert to a list
    dtype : `type`
        Type of data for output
    nelt : `int`
        Required number of elements

    Returns
    -------
    array : `numpy.ndarray`
        ``value`` as a 1-dimensional array with the specified type and length.

    Raises
    ------
    ValueError
        If ``value`` is a sequence of the wrong length
    TypeError
        If ``value`` (if a scalar) or any of its elements (if a sequence)
        cannot be cast to ``dtype``.
    """
    if is_sequence(value):
        if len(value) != nelt:
            raise ValueError(f"len={len(value)} != {nelt}")
        return np.array(value, dtype=dtype)
    return np.array([value] * nelt, dtype=dtype)


class CalSysTakeData(salobj.BaseScript):
    """"""

    def __init__(self, index):
        super().__init__(
            index=index,
            descr="Configure and take data from the auxiliary telescope CalSystem.",
        )
        self.electrometer = salobj.Remote(
            domain=self.domain, name="Electrometer", index=1
        )
        self.monochromator = salobj.Remote(domain=self.domain, name="ATMonochromator")
        self.fiber_spectrograph = salobj.Remote(
            domain=self.domain, name="FiberSpectrograph"
        )
        self.cmd_timeout = 10
        self.change_grating_time = 60

    @classmethod
    def get_schema(cls):
        schema_yaml = """
            $schema: http://json-schema.org/draft-07/schema#
            $id: https://github.com/lsst-ts/ts_standardscripts/auxtel/SlewTelescopeIcrs.yaml
            title: SlewTelescopeIcrs v1
            description: Configuration for SlewTelescopeIcrs.
              Each attribute can be specified as a scalar or array.
              All arrays must have the same length (one item per image).
            type: object
            properties:
              wavelengths:
                description: Wavelength for each image (nm)
                anyOf:
                  - type: array
                    minItems: 1
                    items:
                      type: number
                      exclusiveMinimum: 0
                  - type: number
                    exclusiveMinimum: 0
              integration_times:
                description: Integration time for each image (sec)
                anyOf:
                  - type: array
                    minItems: 1
                    items:
                      type: number
                      exclusiveMinimum: 0
                  - type: number
                    exclusiveMinimum: 0
              grating_types:
                description: Grating type for each image. The choices are 1=blue, 2=red, 3=mirror.
                default: 1
                anyOf:
                  - type: array
                    minItems: 1
                    items:
                      type: integer
                      enum: [1, 2, 3]
                  - type: integer
                    enum: [1, 2, 3]
              entrance_slit_widths:
                description: Width of the monochrometer entrance slit for each image (mm)
                default: 2
                anyOf:
                  - type: array
                    minItems: 1
                    items:
                      type: number
                      exclusiveMinimum: 0
                  - type: number
                    exclusiveMinimum: 0
              exit_slit_widths:
                description: Width of the monochrometer entrance slit for each image (mm)
                default: 4
                anyOf:
                  - type: array
                    minItems: 1
                    items:
                      type: number
                      exclusiveMinimum: 0
                  - type: number
                    exclusiveMinimum: 0
              image_types:
                description: Type of each image.
                default: test
                anyOf:
                  - type: array
                    minItems: 1
                    items:
                      type: string
                  - type: string
              lamps:
                description: Name of lamp for each image.
                default: lamps
                anyOf:
                  - type: array
                    minItems: 1
                    items:
                      type: string
                  - type: string
              spectrometer_delays:
                description: Delay before taking each image (sec).
                default: 1
                anyOf:
                  - type: array
                    minItems: 1
                    items:
                      type: number
                      minimum: 0
                  - type: number
                    minimum: 0
            required:
                - wavelengths
                - integration_times
                - grating_types
                - entrance_slit_widths
                - exit_slit_widths
                - image_types
                - lamps
                - spectrometer_delays
            additionalProperties: false
        """
        return yaml.safe_load(schema_yaml)

    async def configure(self, config):
        """Configure the script.

        Parameters
        ----------
        config : ``self.cmd_configure.DataType``

        Raises
        ------
        salobj.ExpectedError :
            If the data does not match the schema, or the lengths
            of all values that are arrays do not match.
        """
        self.log.info("Configure started")

        nelt = 1
        kwargs = locals()
        # Find the first array value, if any, and set nelt based on that
        for argname in (
            "wavelengths",
            "integration_times",
            "grating_types",
            "entrance_slit_widths",
            "exit_slit_widths",
            "image_types",
            "lamps",
            "spectrometer_delays",
        ):
            value = getattr(config, argname)
            if is_sequence(value):
                nelt = len(value)
                break

        config.wavelengths = as_array(config.wavelengths, dtype=float, nelt=nelt)
        config.integration_times = as_array(
            config.integration_times, dtype=float, nelt=nelt
        )
        config.grating_types = as_array(config.grating_types, dtype=int, nelt=nelt)
        config.entrance_slit_widths = as_array(
            config.entrance_slit_widths, dtype=float, nelt=nelt
        )
        config.exit_slit_widths = as_array(
            config.exit_slit_widths, dtype=float, nelt=nelt
        )
        config.image_types = as_array(config.image_types, dtype=str, nelt=nelt)
        config.lamps = as_array(config.lamps, dtype=str, nelt=nelt)
        config.spectrometer_delays = as_array(
            config.spectrometer_delays, dtype=float, nelt=nelt
        )
        self.config = config

        self.log.info("Configure completed")

    def set_metadata(self, metadata):
        """Compute estimated duration.

        Parameters
        ----------
        metadata : SAPY_Script.Script_logevent_metadataC
        """
        nimages = len(self.config.lamps)
        metadata.duration = self.change_grating_time * nimages + np.sum(
            self.config.integration_times
        )

    async def run(self):
        """Run script."""

        await self.checkpoint("start")

        nelt = len(self.config.wavelengths)
        for i in range(nelt):
            self.log.info(f"take image {i} of {nelt}")

            await self.checkpoint("setup")

            self.monochromator.cmd_changeWavelength.set(
                wavelength=self.config.wavelengths[i]
            )
            await self.monochromator.cmd_changeWavelength.start(
                timeout=self.cmd_timeout
            )

            self.monochromator.cmd_changeSlitWidth.set(
                slit=ATMonochromator.Slit.EXIT,
                slitWidth=self.config.exit_slit_widths[i],
            )
            await self.monochromator.cmd_changeSlitWidth.start(timeout=self.cmd_timeout)

            self.monochromator.cmd_changeSlitWidth.set(
                slit=ATMonochromator.Slit.ENTRY,
                slitWidth=self.config.entrance_slit_widths[i],
            )
            await self.monochromator.cmd_changeSlitWidth.start(timeout=self.cmd_timeout)

            self.monochromator.cmd_selectGrating.set(
                gratingType=self.config.grating_types[i]
            )
            await self.monochromator.cmd_selectGrating.start(
                timeout=self.cmd_timeout + self.change_grating_time
            )

            await self.checkpoint("expose")

            # The electrometer startScanDt command is not reported as done
            # until the scan is done, so start the scan and then start
            # taking the image data
            self.electrometer.cmd_startScanDt.set(
                scanDuration=self.config.integration_times[i]
                + self.config.spectrometer_delays[i] * 2
            )
            coro1 = self.electrometer.cmd_startScanDt.start()
            coro2 = self.start_take_spectrum(i)
            await asyncio.gather(coro1, coro2)

    async def start_take_spectrum(self, index):
        """Wait for ``config.spectrometer_delays``, then take a spectral image.

        Parameters
        ----------
        index : int
            Index of image to take.

        Returns
        -------
        cmd_expose.start : coro
        """
        await self.electrometer.evt_detailedState.next(
            flush=True, timeout=self.cmd_timeout
        )
        await asyncio.sleep(self.config.spectrometer_delays[index])

        timeout = self.config.integration_times[index] + self.cmd_timeout
        self.fiber_spectrograph.cmd_expose.set(
            type=self.config.image_types[index],
            duration=self.config.integration_times[index],
            source=self.config.lamps[index],
        )
        self.log.info(f"take a {self.config.integration_times[index]} second exposure")
        return await self.fiber_spectrograph.cmd_expose.start(timeout=timeout)
