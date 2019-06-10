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

import yaml

from lsst.ts import salobj
from lsst.ts.idl.enums.Script import ScriptState
from lsst.ts import scriptqueue


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
        super().__init__(index=index, descr="Slew the auxiliary telescope to an ICRS position")
        self.atptg = salobj.Remote(domain=self.domain, name="ATPtg")
        self.tracking_started = False

    @classmethod
    def get_schema(cls):
        schema_yaml = """
            $schema: http://json-schema.org/draft-07/schema#
            $id: https://github.com/lsst-ts/ts_standardscripts/auxtel/SlewTelescopeIcrs.yaml
            title: SlewTelescopeIcrs v1
            description: Configuration for SlewTelescopeIcrs
            type: object
            properties:
              ra:
                description: ICRS right ascension (hour)
                type: number
                minimum: 0
                maximum: 24
              dec:
                description: ICRS declination (deg)
                type: number
                minimum: -90
                maximum: 90
              rot_pa:
                description: Desired instrument position angle, Eastwards from North (deg)
                type: number
                default: 0
              target_name:
                type: string
                default: ""
            required: [ra, dec, rot_pa, target_name]
            additionalProperties: false
        """
        return yaml.safe_load(schema_yaml)

    async def configure(self, config):
        """Configure the script.

        Parameters
        ----------
        config : `types.SimpleNamespace`
            Configuration
        """
        self.config = config

    def set_metadata(self, metadata):
        """Compute estimated duration.

        Parameters
        ----------
        metadata : SAPY_Script.Script_logevent_metadataC
        """
        metadata.duration = 1

    async def run(self):
        self.atptg.cmd_raDecTarget.set(
            targetName=self.config.target_name,
            targetInstance=1,  # TargetInstances_current
            frame=2,  # CoordFrame_icrs
            epoch=2000,  # should be ignored: no parallax or proper motion
            equinox=2000,  # should be ignored for ICRS
            ra=self.config.ra,
            declination=self.config.dec,
            parallax=0,
            pmRA=0,
            pmDec=0,
            rv=0,
            dRA=0,
            dDec=0,
            rotPA=self.config.rot_pa,
            rotFrame=1,  # RotFrame_target
            rotMode=2,  # RotMode_field
        )
        self.log.info(f"Start tracking target_name={self.config.target_name}; "
                      f"ra={self.config.ra}, dec={self.config.dec}; rot_pa={self.config.rot_pa}")
        await self.atptg.cmd_raDecTarget.start(timeout=2)

    async def cleanup(self):
        if self.state.state != ScriptState.ENDING:
            # abnormal termination
            if self.tracking_started:
                self.log.warning(f"Terminating with state={self.state.state}: sending stopTracking to ATMCS")
                await self.atmcs.cmd_stopTracking.start(timeout=2)
