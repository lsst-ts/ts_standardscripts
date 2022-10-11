# This file is part of ts_standardscripts
#
# Developed for the LSST Telescope and Site Systems.
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

from lsst.ts import salobj
from typing import Dict
from abc import abstractmethod
from yaml import safe_load
from types import SimpleNamespace

_ATWhiteLightSchema = """
$schema: http://json-schema.org/draft-07/schema#
$id: TODOTODOTODO
title: AuxtelWhiteLightControl{script_suffix} v1
description: Control the auxtel white light system
type: object
properties:
    event_timeout:
        description: Timeout (seconds) to wait for SAL events
        type: number
        default: 30
    lamp_power:
        description: Desired lamp power in Watts
        type: number
        default: 1200
"""

_CSC_CMP_NAME = "ATWhiteLight"


class WhiteLightControlScriptBase(salobj.BaseScript):
    SCRIPT_DESCR_NAME: str = "BaseClass"
    """ White Light Control script base class for Auxtel

        This is a SAL script to control the functions of the auxtel
        white light calibration system.

        Until that is installed, in the meantime it will be able to control
        the red LED dome flat projector on and off in auxtel"""

    def __init__(self, index: int):
        descr = f"Turn the auxtel White Light {self.SCRIPT_DESCR_NAME}"
        super().__init__(index=index, descr=descr)

        self._whitelight = salobj.Remote(self.domain, _CSC_CMP_NAME)

    @classmethod
    def get_schema(cls) -> Dict:
        ourschema = _ATWhiteLightSchema.format(
            script_suffix=cls.SCRIPT_DESCR_NAME.capitalize()
        )
        return safe_load(ourschema)

    async def configure(self, config: SimpleNamespace):
        self._evttimeout: int = config.event_timeout
        self._lamppower: float = config.lamp_power

    def set_metadata(self, metadata):
        pass

    async def run(self) -> None:
        # first check if ATWhiteLight is enabled
        ss = await self._whitelight.evt_summaryState.aget(timeout=self._evttimeout)
        state = salobj.State(ss)

        if state != salobj.State.ENABLED:
            raise AssertionError(
                f"{_CSC_CMP_NAME} needs to be enabled to run this script"
            )

        # now turn on (or off, depending on instantiation) the lamp
        await self._exec_whitelight_onoff_action()

    @abstractmethod
    async def _exec_whitelight_onoff_action(self) -> None:
        ...


class WhiteLightControlScriptTurnOn(WhiteLightControlScriptBase):
    SCRIPT_DESCR_NAME: str = "on"

    async def _exec_whitelight_onoff_action(self) -> None:
        await self._whitelight.cmd_turnLampOn(self._lamppower)


class WhiteLightControlScriptTurnOff(WhiteLightControlScriptBase):
    SCRIPT_DESCR_NAME: str = "off"

    async def _exec_whitelight_onoff_action(self) -> None:
        await self._whitelight.cmd_turnLampOff()
