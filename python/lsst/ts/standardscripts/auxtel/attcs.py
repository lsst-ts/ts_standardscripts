import asyncio 
import logging
from lsst.ts import salobj
import SALPY_ATPtg

class ATTCS:
    """
    High level library for the Auxiliary Telescope Control System

    This is the high level interface for interacting with the CSCs that control the Auxiliary Telescope.
    Essentially this will allow the user to slew and track the telescope.

    Parameters
    ----------
    atmcs: salobj.Remote
    ataos: salobj.Remote
    atpneumatics: salobj.Remote
    athexapod: salobj.Remote
    atdome: salobj.Remote
    atdometrajectory: salobj.Remote

    Attributes
    ----------
    atmcs: salobj.Remote
    ataos: salobj.Remote
    atpneumatics: salobj.Remote
    athexapod: salobj.Remote
    atdome: salobj.Remote
    atdometrajectory: salobj.Remote
    """
    def __init__(self,
            atmcs,
            ataos,
            atpneumatics,
            athexapod,
            atdome,
            atdometrajectory):
        self.atmcs = atmcs
        self.ataos = ataos
        self.atpneumatics=atpneumatics
        self.athexapod=athexapod
        self.atdome=atdome
        self.atdometrajectory=atdometrajectory

    async def slew(self,
            ra,
            declination,
            rotPA=0,
            targetName="slew_icrs",
            targetInstance=SALPY_ATPtg.ATPtg_shared_TargetInstances_current,
            frame=SALPY_ATPtg.ATPtg_shared_CoordFrame_icrs,
            epoch=2000,
            equinox=2000,
            parallax=0,
            pmRA=0,
            pmDec=0,
            rv=0,
            dRA=0,
            dDec=0,
            rotFrame=SALPY_ATPtg.ATPtg_shared_RotFrame_target,
            rotMode=SALPY_ATPtg.AtPtg_shared_RotMode_field):
        """
        Slew the telescope

        Parameters
        ----------
        
        ra: float 
            desired right ascension to slew to
        dec: float 
            desired declination to slew to
        rotPA: float 
            desired rotator position angle for slew
        targetName: str
            Name of the target
        targetInstance
        frame
        epoch
        equinox
        parallax
        pmRA
        pmDec
        rv
        dRA
        rotFrame
        rotMode

        """
        self.atptg.cmd_raDecTarget.set(
                ra=ra,
                declination=declination,
                rotPA=rotPA,
                targetFrame=targetFrame,
                targetInstance=targetInstance,
                frame=frame,
                epoch=epoch,
                equinox=equinox,
                parallax=parallax,
                pmRA=pmRA,
                pmDec=pmDec,
                rv=rv,
                dRA=dRA,
                dDec=dDec,
                rotFrame=rotFrame,
                rotMode=rotMode)
        self.atmcs.ect_allAxesInPosition.flush()
        self.atptg.cmd_raDecTarget.start(timeout=300)
        coro_list= [
                asyncio.ensure_future(self.wait_for_position),
                asyncio.ensure_future(self.check_atptg_state),
                asyncio.ensure_future(self.check_atmcs_state)]
        for res in asyncio.as_completed((coro_list)):
            try:
                await res
            except RuntimeError as rte:
                
                for coro in coro_list:
                    if not coro.done():
                        coro.cancel()
                        try:
                            await coro
                        except asyncio.CancelledError:
                            pass
                raise rte
            else:
                break

    async def check_atmcs_state(self):
        """
        check atmcs state and raise exception if in other state than enabled.
        """
        while True:
            summary_state= await self.atmcs.evt_summaryState.next(flush=False)
            if summary_state.summaryState!=salobj.State.ENABLED:
                raise RuntimeError(f"ATMCS state is {salobj.State(summary_state.summaryState}")

    async def check_atptg_state(self):
        """
        check atptg state and raise exception if in other state than enabled.
        """
        while True:
            summary_state = await self.atptg.evt_summaryState.next(flush=False)
            if summary_state.summaryState!=salobj.State.ENABLED:
                raise RuntimeError(f"ATPtg state is {salobj.State(summary_state.summaryState}")

        

    async def wait_for_position(self):
        """
        Wait for position of atmcs to be ready.
        """
        while True:
            in_position = await self.atmcs.evt_allAxesInPosition.next(flush=False, timeout=20)
            self.log.debug(f"Got {in_position.inPosition}")
            if in_position.inPosition:
                self.logo.info(f"Telescope slew finished")
                break
