.. py:currentmodule:: lsst.ts.standardscripts

.. _lsst.ts.standardscripts.developer_guide:

###############
Developer Guide
###############

.. image:: https://img.shields.io/badge/GitHub-ts_standardscripts-green.svg
    :target: https://github.com/lsst-ts/ts_standardscripts
.. image:: https://img.shields.io/badge/Jenkins-ts_standardscripts-green.svg
    :target: https://tssw-ci.lsst.org/job/LSST_Telescope-and-Site/job/ts_standardscripts/
.. image:: https://img.shields.io/badge/Jira-ts_standardscripts-green.svg
    :target: https://jira.lsstcorp.org/issues/?jql=project%3DDM%20AND%20labels%3Dts_standardscripts

.. _contributing:

Contributing
============

``lsst.ts.standardscripts`` is developed at https://github.com/lsst-ts/ts_standardscripts.
You can find Jira issues for this package using `project=DM and labels=ts_standardscripts <https://jira.lsstcorp.org/issues/?jql=project%3DDM%20AND%20labels%3Dts_standardscripts>`_.

.. _api_ref:

Python API reference
====================

Standard Scripts Core
---------------------
.. automodapi:: lsst.ts.standardscripts
   :no-main-docstr:

.. automodapi:: lsst.ts.standardscripts.scheduler
   :no-main-docstr:

.. automodapi:: lsst.ts.standardscripts.calibration
   :no-main-docstr:

.. _ocs_scripts_api:

OCS Script Classes
------------------

.. automodapi:: lsst.ts.standardscripts.data.scripts.ocs.scheduler.add_block
   :no-main-docstr:
   :no-inheritance-diagram:

.. automodapi:: lsst.ts.standardscripts.data.scripts.ocs.scheduler.enable
   :no-main-docstr:
   :no-inheritance-diagram:

.. automodapi:: lsst.ts.standardscripts.data.scripts.ocs.scheduler.load_snapshot
   :no-main-docstr:
   :no-inheritance-diagram:

.. automodapi:: lsst.ts.standardscripts.data.scripts.ocs.scheduler.resume
   :no-main-docstr:
   :no-inheritance-diagram:

.. automodapi:: lsst.ts.standardscripts.data.scripts.ocs.scheduler.standby
   :no-main-docstr:
   :no-inheritance-diagram:

.. automodapi:: lsst.ts.standardscripts.data.scripts.ocs.scheduler.stop
   :no-main-docstr:
   :no-inheritance-diagram:

Auxiliary Telescope Standardscripts
-----------------------------------
.. automodapi:: lsst.ts.auxtel.standardscripts
   :no-main-docstr:

.. automodapi:: lsst.ts.auxtel.standardscripts.atdome
   :no-main-docstr:

.. automodapi:: lsst.ts.auxtel.standardscripts.calibrations
   :no-main-docstr:

.. automodapi:: lsst.ts.auxtel.standardscripts.daytime_checkout
   :no-main-docstr:

.. automodapi:: lsst.ts.auxtel.standardscripts.detector_characterization
   :no-main-docstr:

.. automodapi:: lsst.ts.auxtel.standardscripts.prepare_for
   :no-main-docstr:

AuxTel Scheduler Scripts
^^^^^^^^^^^^^^^^^^^^^^^^

.. automodapi:: lsst.ts.standardscripts.data.scripts.auxtel.scheduler.add_block
   :no-main-docstr:
   :no-inheritance-diagram:

.. automodapi:: lsst.ts.standardscripts.data.scripts.auxtel.scheduler.enable
   :no-main-docstr:
   :no-inheritance-diagram:

.. automodapi:: lsst.ts.standardscripts.data.scripts.auxtel.scheduler.load_snapshot
   :no-main-docstr:
   :no-inheritance-diagram:

.. automodapi:: lsst.ts.standardscripts.data.scripts.auxtel.scheduler.resume
   :no-main-docstr:
   :no-inheritance-diagram:

.. automodapi:: lsst.ts.standardscripts.data.scripts.auxtel.scheduler.standby
   :no-main-docstr:
   :no-inheritance-diagram:

.. automodapi:: lsst.ts.standardscripts.data.scripts.auxtel.scheduler.stop
   :no-main-docstr:
   :no-inheritance-diagram:

Main Telescope Standardscripts
------------------------------
.. automodapi:: lsst.ts.maintel.standardscripts
   :no-main-docstr:

.. automodapi:: lsst.ts.maintel.standardscripts.calibration
   :no-main-docstr:

.. automodapi:: lsst.ts.maintel.standardscripts.laser_tracker
   :no-main-docstr:

.. automodapi:: lsst.ts.maintel.standardscripts.m1m3
   :no-main-docstr:

.. automodapi:: lsst.ts.maintel.standardscripts.m2
   :no-main-docstr:

.. automodapi:: lsst.ts.maintel.standardscripts.mtdome
   :no-main-docstr:

.. automodapi:: lsst.ts.maintel.standardscripts.mtmount
   :no-main-docstr:

.. automodapi:: lsst.ts.maintel.standardscripts.mtrotator
   :no-main-docstr:

.. automodapi:: lsst.ts.maintel.standardscripts.prepare_for
   :no-main-docstr:

MainTel Scheduler Scripts
^^^^^^^^^^^^^^^^^^^^^^^^^

.. automodapi:: lsst.ts.standardscripts.data.scripts.maintel.scheduler.add_block
   :no-main-docstr:
   :no-inheritance-diagram:

.. automodapi:: lsst.ts.standardscripts.data.scripts.maintel.scheduler.enable
   :no-main-docstr:
   :no-inheritance-diagram:

.. automodapi:: lsst.ts.standardscripts.data.scripts.maintel.scheduler.load_snapshot
   :no-main-docstr:
   :no-inheritance-diagram:

.. automodapi:: lsst.ts.standardscripts.data.scripts.maintel.scheduler.resume
   :no-main-docstr:
   :no-inheritance-diagram:

.. automodapi:: lsst.ts.standardscripts.data.scripts.maintel.scheduler.standby
   :no-main-docstr:
   :no-inheritance-diagram:

.. automodapi:: lsst.ts.standardscripts.data.scripts.maintel.scheduler.stop
   :no-main-docstr:
   :no-inheritance-diagram:
