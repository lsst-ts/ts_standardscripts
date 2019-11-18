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

from lsst.ts import salobj


class ATCalSys:
    """ Implement high level ATCalSys functionality.

    Parameters
    ----------
    domain: `salobj.Domain`
        Domain to use of the Remotes. If `None`, create a new domain.
    electrometer_index : `int`
        Electrometer index.
    fiber_spectrograph_index : `int`
        FiberSpectrograph index.
    """
    def __init__(self, domain=None, electrometer_index=1, fiber_spectrograph_index=-1):

        self.long_timeout = 30.

        self._components = [f"Electrometer:{electrometer_index}",
                            "ATMonochromator",
                            f"FiberSpectrograph:{fiber_spectrograph_index}"]

        self.components = [comp.lower().split(":")[0] for comp in self._components]

        self._remotes = {}

        self.domain = domain if domain is not None else salobj.Domain()

        for i in range(len(self._components)):
            if ":" in self.components[i]:
                name, index = self.components[i].split(":")
                self._remotes[self.components[i]] = salobj.Remote(self.domain,
                                                                  name,
                                                                  int(index))
            else:
                self._remotes[self.components[i]] = salobj.Remote(self.domain,
                                                                  self._components[i])
            setattr(self.check, self.components[i], True)

        self.start_task = asyncio.gather(*[self._remotes[r].start_task for r in self._remotes])

    @property
    def electr(self):
        return self._remotes['electrometer']

    @property
    def monochr(self):
        return self._remotes["atmonochromator"]

    @property
    def fiber_spec(self):
        return self._remotes["fiberspectrograph"]

    @property
    def electrometer(self):
        return self._remotes['electrometer']

    @property
    def atmonochromator(self):
        return self._remotes["atmonochromator"]

    @property
    def fiberspectrograph(self):
        return self._remotes["fiberspectrograph"]

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

        await self.monochr.cmd_updateMonochromatorSetup.start(timeout=self.long_timeout)

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
        lfo_coro = self.electr.evt_largeFileObjectAvailable.next(timeout=self.long_timeout,
                                                                 flush=True)
        await self.electr.cmd_startScanDt.start(timeout=duration+self.long_timeout)

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
        large_file_data : ``fiber_spec.evt_largeFileObjectAvailable.DataType``
            Large file object available event data.
        """
        if evt is not None:
            await evt
        await asyncio.sleep(delay)

        timeout = integration_time + self.long_timeout

        fs_lfo_coro = self.fiber_spec.evt_largeFileObjectAvailable.next(
            timeout=self.long_timeout, flush=True)

        self.fiber_spec.cmd_expose.set(
            imageType=image_type,
            integrationTime=integration_time,
            lamp=lamp,
        )

        await self.fiber_spec.cmd_expose.start(timeout=timeout)

        return await fs_lfo_coro

    async def close(self):
        await asyncio.gather(*[self._remotes[r].close() for r in self._remotes])
        await self.domain.close()

    async def __aenter__(self):
        await self.start_task
        return self

    async def __aexit__(self, *args):

        await self.close()
