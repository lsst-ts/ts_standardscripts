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

from __future__ import annotations
import logging
import unittest
from typing import Optional
from contextlib import asynccontextmanager

from lsst.ts.standardscripts.auxtel import (
    WhiteLightControlScriptTurnOn,
    WhiteLightControlScriptTurnOff,
)
from lsst.ts import standardscripts
from lsst.ts.standardscripts import auxtel
from lsst.ts import salobj


logging.basicConfig(level=logging.DEBUG)


class TestAuxtelWhiteLightScripts(
    standardscripts.BaseScriptTestCase, unittest.IsolatedAsyncioTestCase
):
    TEST_SCRIPTS = [WhiteLightControlScriptTurnOff, WhiteLightControlScriptTurnOn]
    TEST_POWER_VALUE: float = 800.0
    TEST_TIMEOUT_VALUE: int = 35

    def __init__(self, *args, **kwargs):
        super().__init__(*args,**kwargs)
        self._lamp_state: Optional[bool] = None
        
    # NOTE the below is overriding base class with different
    # signature, is that OK??
    async def basic_make_script(self, index: int):
        self.script = self._scripttp(index)
        self.atwhitelight = salobj.Controller(name="ATWhiteLight")

        self.atwhitelight.cmd_turnLampOn.callback = self.cmd_turnon_callback
        self.atwhitelight.cmd_turnLampOff.callbacj = self.cmd_turnoff_callback

        return self.script, self.atwhitelight

    async def cmd_turnon_callback(self):
        self._lamp_state = True

    async def cmd_turnoff_callback(self):
        self._lamp_state = False

    async def test_configure(self):

        for sc in self.TEST_SCRIPTS:
            self._scripttp = sc
            async with self.make_script(sc):
                await self.configure_script(
                    lamp_power=self.TEST_POWER_VALUE,
                    event_timeout=self.TEST_TIMEOUT_VALUE,
                )

                assert self.script._evttimeout == self.TEST_TIMEOUT_VALUE
                assert self.script._lamppower == self.TEST_POWER_VALUE

    async def test_run(self):
        for sc in self.TEST_SCRIPTS:
            self._scripttp = sc
            async with self.make_script(sc):
                await self.configure_script(
                    lamp_power=self.TEST_POWER_VALUE,
                    event_timeout=self.TEST_TIMEOUT_VALUE,
                )

                await self.run_script()
                match type(sc):
                    case auxtel.WhiteLightControlScriptTurnOff:
                        assert self._lamp_state is False
                    case auxtel.WhiteLightControlScriptTurnOn:
                        assert self._lamp_state is True

if __name__ == "__main__":
    unittest.main()
