import yaml
from lsst.ts.salobj import BaseScript
from lsst.ts.observatory.control.auxtel.atcalsys import ATCalsys
from lsst.ts.observatory.control.base_calsys import CalsysScriptIntention
import astropy.units as un


class PowerOnATCalSysNew(BaseScript):
    """Powers on AT calsys ready for calibrations"""

    def __init__(self, index):
        super().__init__(index=index, descr="Power On AT Calibration System")
        self._calsys = ATCalsys(CalsysScriptIntention.TURN_ON, log=self.log)

    @classmethod
    def get_schema(cls):
        schema_yaml = """
            $schema: http://json-schema.org/draft-07/schema#
            $id: https://github.com/lsst-ts/ts_standardscripts/auxtel/calibrations/power_on_newcalsys.yaml
            title: PowerOnATCalSysNew v1
            description: Configuration for PowerOnATCalSysNew.
              Each attribute is nullable, in which case the ATCalsys helper class will decide a sensible
              default, or load current defaults from other sources
            type: object
            properties:
              chiller_temperature:
                description: Set temperature for the chiller
                type: [number, null]
                default: 20
                minimum: 10

              whitelight_power:
                description: White light power (Units of Watts).
                type: [number, null]
                default: 910
                minimum: 0

            additionalProperties: false
        """
        return yaml.safe_load(schema_yaml)

    async def configure(self, config):
        if config.chiller_temperature is not None:
            self._calsys.CHILLER_SETPOINT_TEMP = config.chiller_temperature << un.deg_C
        if config.whitelight_power is not None:
            self._calsys.WHITELIGHT_POWER = config.whitelight_power << un.W

    def set_metadata(self, metadata):
        metadata.duration = self._calsys.script_time_estimate_s

    async def run(self):
        await self._calsys.enable()
        await self.checkpoint("all components enabled, beginning power up sequence")
        await self._calsys.power_sequence_run(self)
