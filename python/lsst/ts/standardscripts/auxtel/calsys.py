# This file is part of ts_standardscripts
#
# Developed for the LSST Data Management System.
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

__all__ = ['ATCalSys']

import asyncio
from .latiss import LATISS


class ATCalSys:
    """ Implement high level ATCalSys functionality.

    Parameters
    ----------
    electr : `lsst.ts.salobj.Remote`
        Remote for the Electrometer.
    monochr : `lsst.ts.salobj.Remote`
        Remote for the Monochromator.
    fiber_spec : `lsst.ts.salobj.Remote`
        Remote for the FiberSpectrograph.
    atcam : `lsst.ts.salobj.Remote`
        Remote for the ATCamera.
    atspec : `lsst.ts.salobj.Remote`
        Remote for the ATSpectrograph.
    atarch : `lsst.ts.salobj.Remote`
        Remote for the ATArchiver.
    """
    def __init__(self, electr, monochr, fiber_spec, atcam, atspec, atarch):

        self.latiss = LATISS(atcam=atcam,
                             atspec=atspec)
        self.electr = electr
        self.monochr = monochr
        self.fiber_spec = fiber_spec
        self.atarch = atarch

        self.cmd_timeout = 30.

    async def setup_monochromator(self, wavelength, entrance_slit, exit_slit, grating):
        """Setup Monochromator.



        Parameters
        ----------
        wavelength : `float`
            Wavelength in nm.
        entrance_slit : `float`
            Size of entrance slit in mm.
        exit_slit : `float`
            Size of exist slit in mm.
        grating : `int`
            Grating to select.

        """

        self.monochr.cmd_updateMonochromatorSetup.set(wavelength=wavelength,
                                                      gratingType=grating,
                                                      fontExitSlitWidth=exit_slit,
                                                      fontEntranceSlitWidth=entrance_slit)

        await self.monochr.cmd_updateMonochromatorSetup.start(timeout=self.cmd_timeout)

    async def electrometer_scan(self, duration):
        """Perform an electrometer scan for the specified duration and return
        a large file object event.

        Parameters
        ----------
        duration : `float`
            Total duration of scan.

        Returns
        -------
        lfo : ``self.electr.evt_largeFileObjectAvailable.DataType``
            Large file Object Available event.

        """
        self.electr.cmd_startScanDt.set(scanDuration=duration)
        lfo_coro = self.electr.evt_largeFileObjectAvailable.next(timeout=self.cmd_timeout,
                                                                 flush=True)
        await self.electr.cmd_startScanDt.start(timeout=duration+self.cmd_timeout)

        return await lfo_coro

    async def take_fiber_spectrum_after(self, delay, image_type, integration_time, lamp, evt=None):
        """Wait, then start an acquisition with the fiber spectrograph.

        By default, this method will wait for `delay` seconds then start
        an acquisition with the fiber spectrograph. Optionally the user may
        provide a coroutine that will be awaited before the delay starts.

        Parameters
        ----------
        delay : `float`
            Seconds to wait before starting fiber spectrograph acquisition.
        image_type : `str`
            Type of each image.
        integration_time : `float`
            Integration time for the fiber spectrum (seconds).
        lamp : `str`
            Name of lamp for each image.
        evt : `coro`
            An awaitable that will be waited before delay and processing. If
            None, ignored.

        Returns
        -------
        large_file_data : ``self.fiber_spec.evt_largeFileObjectAvailable.DataType``
            Large file object available event data.
        """
        if evt is not None:
            await evt
        await asyncio.sleep(delay)

        timeout = integration_time + self.cmd_timeout

        fs_lfo_coro = self.fiber_spec.evt_largeFileObjectAvailable.next(
            timeout=self.cmd_timeout, flush=True)

        self.fiber_spec.cmd_captureSpectImage.set(
            imageType=image_type,
            integrationTime=integration_time,
            lamp=lamp,
        )

        await self.fiber_spec.cmd_captureSpectImage.start(timeout=timeout)

        return await fs_lfo_coro
