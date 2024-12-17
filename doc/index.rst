.. py:currentmodule:: lsst.ts.auxtel.standardscripts

.. _auxtel_standardscripts:

################
Standard Scripts
################

.. image:: https://img.shields.io/badge/GitHub-ts_auxtel_standardscripts-green.svg
    :target: https://github.com/lsst-ts/ts_auxtel_standardscripts
.. image:: https://img.shields.io/badge/Jenkins-ts_auxtel_standardscripts-green.svg
    :target: https://tssw-ci.lsst.org/job/LSST_Telescope-and-Site/job/ts_auxtel_standardscripts/
.. image:: https://img.shields.io/badge/Jira-ts_auxtel_standardscripts-green.svg
    :target: https://jira.lsstcorp.org/issues/?jql=project%3DDM%20AND%20labels%3Dts_auxtel_standardscripts

Overview
========

The standard SAL scripts run by the `script queue <https://ts-scriptqueue.lsst.io>`_.

User Documentation
==================

To add a script to this package:

* Read `SAL Scripts <https://ts-salobj.lsst.io/sal_scripts.html>`_ to learn the basics of writing a SAL script.
* Add your script implementation to the library: ``python/lsst/ts/auxtel/standardscripts``.
* Add a test suite to the ``tests`` directory.
* Add a bin script to the ``python/lsst/ts/auxtel/standardscripts/data/scripts`` directory.

Developer Documentation
=======================

.. toctree::
    developer_guide
    :maxdepth: 1

Version History
===============

.. toctree::
    version_history
    :maxdepth: 1
