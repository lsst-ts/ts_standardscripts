.. py:currentmodule:: lsst.ts.standardscripts

.. _standardscripts:

################
Standard Scripts
################

.. image:: https://img.shields.io/badge/GitHub-ts_standardscripts-green.svg
    :target: https://github.com/lsst-ts/ts_standardscripts
.. image:: https://img.shields.io/badge/Jenkins-ts_standardscripts-green.svg
    :target: https://tssw-ci.lsst.org/job/LSST_Telescope-and-Site/job/ts_standardscripts/
.. image:: https://img.shields.io/badge/Jira-ts_standardscripts-green.svg
    :target: https://jira.lsstcorp.org/issues/?jql=labels+%3D+ts_standardscripts

Overview
========

The standard SAL scripts run by the `script queue <https://ts-scriptqueue.lsst.io>`_.

User Documentation
==================

To add a script to this package:

* Read `SAL Scripts <https://ts-salobj.lsst.io/sal_scripts.html>`_ to learn the basics of writing a SAL script.
* Add your script implementation to the library: ``python/lsst/ts/standardscripts``.
* Add a test suite to the ``tests`` directory.
* Add a bin script to the ``scripts`` directory.

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
