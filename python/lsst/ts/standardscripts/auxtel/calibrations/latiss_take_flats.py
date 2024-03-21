import yaml
from lsst.ts.salobj import BaseScript
from lsst.ts.observatory.control.auxtel.atcalsys import ATCalsys
from lsst.ts.observatory.control.base_calsys import CalsysScriptIntention

class LatissTakeCalibrationFlats(BaseScript):
    """Takes calibration flats with LATISS"""

    def __init__(self, index):
        super().__init__(index=index, descr="Take calibration flats with LATISS")
        self._calsys = ATCalsys(CalsysScriptIntention.QUICK_CALIBRATION_RUN, log=self.log)

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
          n_exposures:
              description: number of flat field exposures to take with LATISS
              type: number
              default: 1
          latiss_filter:
              description: filter to use to take the calibration
              type: string
              default: 'empty_1'
          latiss_grating:
              description: Grating to use to take the calibration
              type: string
              default: 'empty_1'
          wavelength:
              description: wavelength to use (unit nm). If null will be looked up from configuration
              type: [null, number]
              default: null
          exit_slit_width:
              description: exit slit width to use (unit mm). If null will be calculated based on other parameters e.g. spectral resolution
              type: [null, number]
          entrance_slit_width:
              description: entrance slit width to use (unit mm). If null will be calculated based on other parameters e.g. spectral resolution
              type: [null, number]
              default: null
          exposure_time:
              description: exposure time to use for LATISS images (unit seconds). If null will be calculated based on lamp power, requested flat field level and throughput calibrations
              type: [null, number]
              default: null
          exposure_kelec:
              description: target exposure of the lATISS flats (unit electrons). Must not be specified along with exposure_time
              type: [null, number]
              default: 50
          spec_res:
              description: spectral resolution target for the flat field (unit nm). If exit_slit_width and entrance_slit_width are explicitly provided this must not be
              type: [null, number]
              default: null

        additionalProperties: false """
        return yaml.safe_load(schema_yaml)

    async def configure(self, config) -> None:
        pass

    def set_metadata(self, metadata) -> None:
        metadata.duration = self._calsys.script_time_estimate_s

    async def run(self) -> None:
        await self._calsys.enable()
        await self.checkpoint("all component enabled, proceeding with flat field acquisition")
