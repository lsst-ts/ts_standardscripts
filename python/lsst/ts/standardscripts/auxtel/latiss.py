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

__all__ = ['LATISS']

import asyncio

from lsst.ts import salobj


class LATISS:
    """LSST Auxiliary Telescope Image and Slit less Spectrograph.

    Implement high level functionality for LATISS, a high level instrument
    which is the combination of ATCamera, ATSpectrograph, ATHeaderService and
    ATArchiver CSCs.

    Parameters
    ----------
    domain : `lsst.ts.salobj.Domain`
        Domain for remotes. If `None` create a domain.
    """

    def __init__(self, domain=None):

        self._components = ["ATCamera", "ATSpectrograph", "ATHeaderService", "ATArchiver"]

        self.components = [comp.lower() for comp in self._components]

        self._remotes = {}

        self.domain = domain if domain is not None else salobj.Domain()

        for i in range(len(self._components)):
            self._remotes[self.components[i]] = salobj.Remote(self.domain,
                                                              self._components[i])

        self.start_task = asyncio.gather(*[self._remotes[r].start_task for r in self._remotes])

        self.read_out_time = 2.  # readout time (sec)
        self.shutter_time = 1  # time to open or close shutter (sec)

        self.fast_timeout = 5.
        self.long_timeout = 30.
        self.long_long_timeout = 120.

        self.cmd_lock = asyncio.Lock()

    @property
    def atcamera(self):
        return self._remotes["atcamera"]

    @property
    def atspectrograph(self):
        return self._remotes["atspectrograph"]

    @property
    def atheaderservice(self):
        return self._remotes["atheaderservice"]

    @property
    def atarchiver(self):
        return self._remotes["atarchiver"]

    async def take_bias(self, nbias, checkpoint=None):
        """Take a series of bias images.

        Parameters
        ----------
        nbias : `int`
            Number of bias frames to take.
        checkpoint : `coro`
            A optional awaitable callback that accepts one string argument
            that is called before each bias is taken.

        """
        for i in range(nbias):
            tag = f'bias_{i+1:04}_{nbias:04}'

            if checkpoint is not None:
                await checkpoint(tag)
            await self.expose(exp_time=0., shutter=False,
                              image_type="BIAS",
                              group_id=tag,
                              science=True, guide=False, wfs=False)

    async def take_darks(self, exptime, ndarks, checkpoint=None):
        """Take a series of dark images.

        Parameters
        ----------
        exptime : `float`
            Exposure time for darks.
        ndarks : `int`
            Number of dark frames to take.
        checkpoint : `coro`
            A optional awaitable callback that accepts one string argument
            that is called before each bias is taken.

        """
        for i in range(ndarks):
            tag = f'dark_{i+1:04}_{ndarks:04}'
            if checkpoint is not None:
                await checkpoint(tag)
            await self.expose(exp_time=exptime, shutter=False,
                              image_type="DARK",
                              group_id=tag,
                              science=True, guide=False, wfs=False)

    async def take_flats(self, exptime, nflats,
                         filter=None, grating=None, linear_stage=None,
                         checkpoint=None):
        """Take a series of flat field images.

        Parameters
        ----------
        exptime : `float`
            Exposure time for flats.
        nflats : `int`
            Number of flat frames to take.
        filter : `None` or `int` or `str`
            Filter id or name. If None, do not change the filter.
        grating : `None` or `int` or `str`
            Grating id or name.  If None, do not change the grating.
        linear_stage : `None` or `float`
            Linear stage position.  If None, do not change the linear stage.
        checkpoint : `coro`
            A optional awaitable callback that accepts one string argument
            that is called before each bias is taken.

        """
        for i in range(nflats):
            tag = f"flat_{i+1:04}"
            if checkpoint is not None:
                await checkpoint(tag)
            await self.take_image(exptime=exptime, shutter=True, image_type="FLAT",
                                  group_id=tag,
                                  filter=filter, grating=grating,
                                  linear_stage=linear_stage)

    async def take_image(self, exptime, shutter, image_type, group_id,
                         filter=None, grating=None, linear_stage=None,
                         science=True, guide=False, wfs=False,
                         ):
        """Set up the spectrograph and take a series of images.


        Setting up the spectrograph and taking images cannot be done
        concurrently. One needs first to setup the spectrograph then,
        request images.

        Parameters
        ----------
        exptime : `float`
            The exposure time for the image, in seconds.
        shutter : `bool`
            Should activate the shutter? (False for bias and dark)
        image_type : `str`
            Image type (a.k.a. IMGTYPE) (e.g. e.g. BIAS, DARK, FLAT, FE55,
            XTALK, CCOB, SPOT...)
        group_id : `str`
            Image groupId. Used to fill in FITS GROUPID header
        grating : `None` or `int` or `str`
            Grating id or name.  If None, do not change the grating.
        linear_stage : `None` or `float`
            Linear stage position.  If None, do not change the linear stage.
        science : `bool`
            Mark image as science (default=True)?
        guide : `bool`
            Mark image as guide (default=False)?
        wfs : `bool`
            Mark image as wfs (default=False)?

        Returns
        -------
        endReadout : ``self.atcam.evt_endReadout.DataType``
            End readout event data.
        """

        await self.setup_atspec(filter=filter,
                                grating=grating,
                                linear_stage=linear_stage)

        return await self.expose(exp_time=exptime, shutter=shutter,
                                 image_type=image_type,
                                 group_id=group_id,
                                 science=science, guide=guide, wfs=wfs)

    async def expose(self, exp_time, shutter, image_type, group_id,
                     science=True, guide=False, wfs=False):
        """Encapsulates the take image command.

        This basically consists of configuring and sending a takeImages
        command to the camera and waiting for an endReadout event.

        Parameters
        ----------
        exp_time : `float`
            The exposure time for the image, in seconds.
        shutter : `bool`
            Should activate the shutter? (False for bias and dark)
        image_type : `str`
            Image type (a.k.a. IMGTYPE) (e.g. e.g. BIAS, DARK, FLAT, FE55,
            XTALK, CCOB, SPOT...)
        group_id : `str`
            Image groupId. Used to fill in FITS GROUPID header
        science : `bool`
            Mark image as science (default=True)?
        guide : `bool`
            Mark image as guide (default=False)?
        wfs : `bool`
            Mark image as wfs (default=False)?

        Returns
        -------
        endReadout : ``self.atcam.evt_endReadout.DataType``
            End readout event data.
        """
        async with self.cmd_lock:
            # FIXME: Current version of ATCamera software is not set up to take
            # images with numImages > 1, so this is fixed at 1 for now and we
            # loop through any set of images we want to take. (2019/03/11)
            self.atcamera.cmd_takeImages.set(numImages=1,
                                             expTime=float(exp_time),
                                             shutter=bool(shutter),
                                             imageType=str(image_type),
                                             groupId=str(group_id),
                                             science=bool(science),
                                             guide=bool(guide),
                                             wfs=bool(wfs)
                                             )

            timeout = self.read_out_time + self.long_timeout + self.long_long_timeout
            self.atcamera.evt_endReadout.flush()
            await self.atcamera.cmd_takeImages.start(timeout=timeout + exp_time)
            return await self.atcamera.evt_endReadout.next(flush=False, timeout=timeout)

    async def setup_atspec(self, filter=None, grating=None,
                           linear_stage=None):
        """Encapsulates commands to setup spectrograph.

        Parameters
        ----------
        filter : `None` or `int` or `str`
            Filter id or name. If None, do not change the filter.
        grating : `None` or `int` or `str`
            Grating id or name.  If None, do not change the grating.
        linear_stage : `None` or `float`
            Linear stage position.  If None, do not change the linear stage.

        """

        setup_coroutines = []
        if filter is not None:
            if isinstance(filter, int):
                self.atspectrograph.cmd_changeFilter.set(filter=filter,
                                                         name='')
            elif type(filter) == str:
                self.atspectrograph.cmd_changeFilter.set(filter=0,
                                                         name=filter)
            else:
                raise RuntimeError(f"Filter must be a string or an int, got "
                                   f"{type(filter)}:{filter}")
            setup_coroutines.append(self.atspectrograph.cmd_changeFilter.start(timeout=self.long_timeout))

        if grating is not None:
            if isinstance(grating, int):
                self.atspectrograph.cmd_changeDisperser.set(disperser=grating,
                                                            name='')
            elif type(grating) == str:
                self.atspectrograph.cmd_changeDisperser.set(disperser=0,
                                                            name=grating)
            else:
                raise RuntimeError(f"Grating must be a string or an int, got "
                                   f"{type(grating)}:{grating}")
            setup_coroutines.append(self.atspectrograph.cmd_changeDisperser.start(timeout=self.long_timeout))

        if linear_stage is not None:
            self.atspectrograph.cmd_moveLinearStage.set(distanceFromHome=float(linear_stage))
            setup_coroutines.append(self.atspectrograph.cmd_moveLinearStage.start(timeout=self.long_timeout))

        if len(setup_coroutines) > 0:
            async with self.cmd_lock:
                return await asyncio.gather(*setup_coroutines)

    async def close(self):
        await asyncio.gather(*[self._remotes[r].close() for r in self._remotes])
        await self.domain.close()

    async def __aenter__(self):
        await self.start_task
        return self

    async def __aexit__(self, *args):

        await self.close()
