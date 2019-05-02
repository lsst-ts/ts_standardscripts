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

__all__ = ["SlewTelescopeIcrs"]

from lsst.ts import salobj
from lsst.ts import scriptqueue

import SALPY_ATMCS
import SALPY_ATPtg


class SlewTelescopeIcrs(scriptqueue.BaseScript):
    """Slew the telescope to a specified ICRS position.

    Parameters
    ----------
    index : `int`
        Index of Script SAL component.

    Notes
    -----
    **Checkpoints**

    * slew: just before sending the ``raDecTarget`` to ATPtg.
        This is primarily intended for unit testing.
        Warning: if you configure the script with ``send_start_tracking=True``
        and pause at the "slew" checkpoint you will send ATPtg
        into a FAULT state!

    **Details**

    This is what the script does:

    * Check that ATPtg and ATMCS are both enabled.
    * Optionally issues the ``startTracking`` command to ATMCS.
    * Issues the ``raDecTarget`` command to ATPtg.
    * If stopped or on failure and ``startTracking`` was issued
        then issues the ``stopTracking`` command to ATMCS.
    """
    __test__ = False  # stop pytest from warning that this is not a test

    def __init__(self, index):
        atmcs = salobj.Remote(SALPY_ATMCS, 0)
        atptg = salobj.Remote(SALPY_ATPtg, 0)
        super().__init__(index=index,
                         descr="Test integration between ATPtg and ATMCS",
                         remotes_dict=dict(atmcs=atmcs, atptg=atptg))
        self.tracking_started = False

    async def configure(self, ra, dec, rot_pa=0, target_name="",
                        send_start_tracking=True):
        """Configure the script.

        Parameters
        ----------
        ra : `float`
            Right ascension (deg).
        dec : `float`
            Declination (deg).
        rot_pa : `float` (optional)
            Position angle (deg).
        send_start_tracking : `bool` (optional)
            Issue the ``startTracking`` command to ATMCS?
            This is presently necessary but ATPtg will soon do it.
            TODO: remote this argument once ATPtg is updated.
        """
        self.dec = float(dec)
        self.ra = float(ra)
        self.rot_pa = float(rot_pa)
        self.target_name = str(target_name)
        self.send_start_tracking = send_start_tracking

    def set_metadata(self, metadata):
        """Compute estimated duration.

        Parameters
        ----------
        metadata : SAPY_Script.Script_logevent_metadataC
        """
        metadata.duration = 1

    async def run(self):
        for csc in (self.atmcs, self.atptg):
            data = csc.evt_summaryState.get()
            if data.summaryState != salobj.State.ENABLED:
                raise RuntimeError(f"{csc.salinfo.name} in state {data.summaryState} "
                                   f"instead of {salobj.State.ENABLED!r}")

        if self.send_start_tracking:
            self.log.info("Send startTracking to ATMCS")
            await self.atmcs.cmd_startTracking.start(timeout=2)
            self.tracking_started = True

        await self.checkpoint("slew")
        self.atptg.cmd_raDecTarget.set(
            targetName=self.target_name,
            targetInstance=SALPY_ATPtg.ATPtg_shared_TargetInstances_current,
            frame=SALPY_ATPtg.ATPtg_shared_CoordFrame_icrs,
            epoch=2000,  # should be ignored: no parallax or proper motion
            equinox=2000,  # should be ignored for ICRS
            ra=self.ra,
            declination=self.dec,
            parallax=0,
            pmRA=0,
            pmDec=0,
            rv=0,
            dRA=0,
            dDec=0,
            rotPA=self.rot_pa,
            rotFrame=SALPY_ATPtg.ATPtg_shared_RotFrame_target,
            rotMode=SALPY_ATPtg.ATPtg_shared_RotMode_field,
        )
        self.log.info(f"Start tracking target_name={self.target_name}; "
                      f"ra={self.ra}, dec={self.dec}; rot_pa={self.rot_pa}")
        await self.atptg.cmd_raDecTarget.start(timeout=2)

    async def cleanup(self):
        if self.state.state != scriptqueue.ScriptState.ENDING:
            # abnormal termination
            if self.tracking_started:
                self.log.warning(f"Terminating with state={self.state.state}: sending stopTracking to ATMCS")
                await self.atmcs.cmd_stopTracking.start(timeout=2)
