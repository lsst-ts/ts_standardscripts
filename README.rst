##################
ts_standardscripts
##################

Standard SAL scripts for operating the LSST via the `lsst.ts.scriptqueue.ScriptQueue`.
Each script is a subclass of `lsst.ts.scriptqueue.ScriptBase`.

Put common code and complicated implementations in ``python/lsst/ts/standardscripts``
and the actual scripts in `scripts` in the desired hierarchy.
