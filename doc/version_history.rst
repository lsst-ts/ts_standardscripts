.. py:currentmodule:: lsst.ts.standardscripts

.. _lsst.ts.standardscripts.version_history:

===============
Version History
===============

v1.13.0
-------

* In ``BaseTrackTarget``:

  * Update schema to have a ``slew_icr`` session and a ``find_target`` session.
    The first works the same way the previous ra/dec parameters worked, the second will find a target around the specified az/el coordinate to track.

* In ``AuxTel/PrepareForOnsky`` add configuration to allow users to ignore certain CSCs.
* Add unit tests for ``prepare_for_onsky`` script.


v1.12.1
-------

* Wait for SalInfo instances to start before writing messages:

    * Call ``super().start()`` first in overrides of start methods.
    * test_auxtel_stop.py: await self.controller.start_task before writing.

* Remove ``cls`` argument from abstract static methods.
* doc/conf.py: make linters happier
* git ignore .hypothesis

v1.12.0
-------

* Add ``BaseTakeStuttered`` script to take stuttered images.
* In ``BaseTakeImage``, add option to take acquisition images.
* Add ``TakeStutteredLatiss`` script to take stuttered images with LATISS.
* In ``GetStdFlatDataset``, pass ``group_id`` to ``take_bias``, ``take_flats`` and ``take_darks`` to group data together.
* Update ``GetStdFlatDataset`` unit test to reduce script test time by reducing the exposure time for darks and using a smaller sequence of flat-fields.

v1.11.0
-------

* In ``auxtel/track_target_and_take_image`` implement taking data with n>1.
* Fix ``tests/test_auxtel_detector_characterization_std_flat_dataset.py`` to take into account snaps.
* In ``auxtel/track_target_and_take_image`` script, implement a rotator flipping routine.
  First it will try to slew the telescope with the provided rotation angle, if that doesn't work, flip 180 degrees and try again.
* Add unit tests for the load snapshot scheduler scripts.
* Add unit tests for the stop scheduler scripts.
* Add unit tests for the resume scheduler scripts.
* Add unit tests for the standby scheduler scripts.
* Add unit tests for the enable scheduler scripts.
* Add executables for the main telescope scheduler operational scripts.
* Add executables for the auxiliary telescope scheduler operational scripts.
* Add scheduler operations scripts for the Main Telescope.
* Add scheduler operations scripts for the Auxiliary Telescope.
* Add test utilities for the scheduler operational scripts.
* Add scheduler submodule with base scripts for operating the Scheduler.
  These are generic implementations that can be used for both the AT and MT schedulers.
* Update setup.cfg to specify async_mode for pytest.
    
v1.10.1
-------

* Make auxtel/prepare_for_onsky.py script not gather ATCS config and just assert enabled.

v1.10.0
-------

* Change archiver references to oods ones due to image creation process change (DMTN-143).

v1.9.0
------

* Update for ts_salobj v7, which is required.
  This also requires ts_xml 11.

v1.8.0
------

* In `BaseTrackTargetAndTakeImage` allow filter to be a list or a single string.
* In `auxtel.TrackTargetAndTakeImage`, allow grating to be a list or a string, implement handling of list of grating/filters.
* Update unit tests for `auxtel.TrackTargetAndTakeImage` to account for handling lists of filters/grating.
* In `auxtel.TrackTargetAndTakeImage` add prefix for filter name.
* Update to use ts_utils

v1.7.0
------

* Implement new reason/program image feature on auxtel and comcam scripts.

v1.6.9
------

* Remove AuxTel integration test scripts (some of which were broken).
  Integration tests now use Jupyter notebooks.
* Remove unnecessary `__test__ = False` statements.
  These are only useful for classes whose names begin with "Test".
* Modernize the unit tests to use bare assert.
* Clean up the package documentation.

v1.6.8
------

* Add new BaseTrackTargetAndTakeImage script, that implements a simple script to track a target and take images.
* Update auxtel/track_target_and_take_image script to use the new BaseTrackTargetAndTakeImage.
* Adds maintel/track_target_and_take_image_comcam script to do a simple track target and take image with the Main Telescope and ComCam.

v1.6.7
------

* Add track target and take image script for auxtel.
* Add stop tracking scrit for auxtel.

v1.6.6
------

* Update prepare for onsky Script to check that LATISS components are enabled before executing.
* Fix import statement in `prepare_for_onsky`

v1.6.5
------

* Update `BaseTakeImage`:

  * Add instrument setup time to duration estimation.
  * Only setup instrument configuration in the first image.
  * Update unit tests.

v1.6.4
------

* Use unittest instead of the deprecated asynctest package.

v1.6.3
------

* Add offline scripts for auxtel.
* Add offline scripts for maintel.
* Update ``tests/SConscript`` to make scons work when building with the licensed version of OpenSplice.

v1.6.2
------

* Reformat code using black 20.
* Enabled pytest-black.
* Pin version of ts-conda-build to 0.3 in conda recipe.
* Update documentation format.
