
import asyncio
import numpy as np

__all__ = ['LATISS']


class LATISS:
    """LSST Auxiliary Telescope Image and Slit less Spectrograph.

    Implement high level functionality for LATISS, a high level instrument
    which is the combination of ATCamera and ATSpectrograph CSCs.

    Parameters
    ----------
    atcam : `lsst.ts.salobj.Remote`
        Remote for the ATCamera.
    atspec : `lsst.ts.salobj.Remote`
        Remote for the ATSpectrograph.
    """

    def __init__(self, atcam, atspec):

        self.atcam = atcam
        self.atspec = atspec

        self.read_out_time = 2.  # readout time (sec)
        self.shutter_time = 1  # time to open or close shutter (sec)

        self.cmd_timeout = 30.
        self.end_readout_timeout = 60.

        self.cmd_lock = asyncio.Lock()

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
                              image_seq_name=tag,
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
                              image_seq_name=tag,
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
            await self.take_image(exptime=exptime, shutter=True, image_seq_name=tag,
                                  filter=filter, grating=grating,
                                  linear_stage=linear_stage)

    async def take_image(self, exptime, shutter, image_seq_name,
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
        image_seq_name : `str`
            A string to identify the image.
        filter : `None` or `int` or `str`
            Filter id or name. If None, do not change the filter.
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
        endReadout : `SALPY_ATCamera.ATCamera_logevent_endReadoutC`

        """

        await self.setup_atspec(filter=filter,
                                grating=grating,
                                linear_stage=linear_stage)

        return await self.expose(exp_time=exptime, shutter=shutter, image_seq_name=image_seq_name,
                                 science=science, guide=guide, wfs=wfs)

    async def expose(self, exp_time, shutter, image_seq_name,
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
        image_seq_name : `str`
            A string to identify the image.
        science : `bool`
            Mark image as science (default=True)?
        guide : `bool`
            Mark image as guide (default=False)?
        wfs : `bool`
            Mark image as wfs (default=False)?

        Returns
        -------
        endReadout : `SALPY_ATCamera.ATCamera_logevent_endReadoutC`

        """
        async with self.cmd_lock:
            # FIXME: Current version of ATCamera software is not set up to take
            # images with numImages > 1, so this is fixed at 1 for now and we
            # loop through any set of images we want to take. (2019/03/11)
            self.atcam.cmd_takeImages.set(numImages=1,
                                          expTime=float(exp_time),
                                          shutter=bool(shutter),
                                          imageSequenceName=str(image_seq_name),
                                          science=bool(science),
                                          guide=bool(guide),
                                          wfs=bool(wfs)
                                          )

            timeout = self.read_out_time + self.cmd_timeout + self.end_readout_timeout

            end_readout_coro = self.atcam.evt_endReadout.next(flush=True,
                                                              timeout=timeout)

            await self.atcam.cmd_takeImages.start(timeout=timeout+exp_time)
            return await end_readout_coro

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
            if np.issubdtype(type(filter), int):
                self.atspec.cmd_changeFilter.set(filter=filter,
                                                 name='')
            elif type(filter) == str:
                self.atspec.cmd_changeFilter.set(filter=0,
                                                 name=filter)
            else:
                raise RuntimeError(f"Filter must be a string or an int, got "
                                   f"{type(filter)}:{filter}")
            setup_coroutines.append(self.atspec.cmd_changeFilter.start(timeout=self.cmd_timeout))

        if grating is not None:
            if np.issubdtype(type(grating), int):
                self.atspec.cmd_changeDisperser.set(disperser=grating,
                                                    name='')
            elif type(grating) == str:
                self.atspec.cmd_changeDisperser.set(disperser=0,
                                                    name=grating)
            else:
                raise RuntimeError(f"Grating must be a string or an int, got "
                                   f"{type(grating)}:{grating}")
            setup_coroutines.append(self.atspec.cmd_changeDisperser.start(timeout=self.cmd_timeout))

        if linear_stage is not None:
            self.atspec.cmd_moveLinearStage.set(distanceFromHome=float(linear_stage))
            setup_coroutines.append(self.atspec.cmd_moveLinearStage.start(timeout=self.cmd_timeout))

        if len(setup_coroutines) > 0:
            async with self.cmd_lock:
                return await asyncio.gather(*setup_coroutines)
