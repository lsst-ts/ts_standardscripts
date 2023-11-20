import asyncio
import yaml
from lsst.ts import salobj
from lsst.ts.observatory.control.auxtel.atcalsys import ATCalsys

class PowerOnATCalSys(salobj.BaseScript):
    """ Powers on teh ATCalsys ready for daily (or monochromated) flat field calibrations """

    def __init__(self, index, add_remotes: bool=True):
        super().__init__(index=index, descr="Power On AT Calibration System")
        self._calsys = ATCalsys(log=self.log)

    @classmethod
    def get_schema(cls):
        schema_yaml = """
                $schema: http://json-schema.org/draft-07/schema#
            $id: https://github.com/lsst-ts/ts_standardscripts/auxtel/calibrations/power_on_atcalsys.yaml
            title: PowerOnATCalSys v1
            description: Configuration for PowerOnATCalSys.
              Each attribute can be specified as a scalar or array.
              All arrays must have the same length (one item per image).
            type: object
            properties:
              chiller_temperature:
                description: Set temperature for the chiller
                type: number
                default: 20
                minimum: 10

              whitelight_power:
                description: White light power.
                type: number
                default: 910
                minimum: 0

              wavelength:
                description: Wavelength (nm). 0 nm is for white light.
                type: number
                default: 0
                minimum: 0

              grating_type:
                description: Grating type for each image. The choices are 0=blue, 1=red, 2=mirror.
                type: integer
                enum: [0, 1, 2]
                default: 2

              entrance_slit_width:
                description: Width of the monochrometer entrance slit (mm)
                type: number
                minimum: 0
                default: 7

              exit_slit_width:
                description: Width of the monochromator entrance slit (mm)
                type: number
                minimum: 0
                default: 7

              use_atmonochromator:
                description: Is the monochromator available and can be configured?
                    If False, the monochromator will be left as it is.
                    If True, the monochromator will be configured for white light.
        type: boolean
                default: false

            additionalProperties: false
        """
        return yaml.safe_load(schema_yaml)

    async def configure(self, config):
        
        pass
