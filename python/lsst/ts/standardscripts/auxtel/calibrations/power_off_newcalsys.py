from lsst.ts.salobj import BaseScript
from lsst.ts.observatory.control.auxtel.atcalsys import ATCalsys
from lsst.ts.observatory.control.base_calsys import CalsysScriptIntention


class PowerOffATCalSysNew(salobj.BaseScript):
    """ Powers off AT calsys """
    def __init__(self, index, add_remotes: bool=True):
        super().__init__(index=index, descr= "Power off AT calibration system")
        self._calsys = ATCalsys(CalsysScriptIntention.TURN_OFF, log=self.log)

    @classmethod
    def get_schema(cls):
        return None

    async def configure(self, config): ...

    def set_metadata(self, metadata):
        metadata.duration = self._calsys.script_time_estimate_s

    async def run(self):
        await self._calsys.enable()
        await self.checkpoint("all components enabled, beginning power down sequence")
        await self._calsys.power_sequence_run(self)
