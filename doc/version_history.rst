.. py:currentmodule:: lsst.ts.standardscripts

.. _lsst.ts.standardscripts.version_history:

===============
Version History
===============

v1.20.0
-------

* Add new ``base_offset_tcs.py`` script to offset generic tcs class. 
* Add new ``auxtel/offset_atcs.py`` script to offset the ATCS. 
* Add new ``maintel/offset_,tcs.py`` script to offset the MTCS. 

* Add new ``auxtel/latiss_take_sequence.py`` script, unit tests, and executables.
* Add new ``maintel/m1m3/raise_m1m3.py`` to raise MainTel M1M3 mirror. 
* Add new ``laser_tracker/set_up.py`` script to set up and turn on the laser tracker.
* Add new ``laser_tracker/shut_down.py`` script to switch off the laser tracker.
* Add new ``laser_tracker/align.py`` script to align mtcs with laser tracker.
* Add new ``maintel/prepare_for/align.py`` script to prepare for align mtcs with laser tracker.

v1.19.2
-------

* In ``auxtel/daytime_checkout/slew_and_take_image_checkout.py``:
  * add check that M3 is in position for observations with LATISS
  * update unit test ``tests/test_auxtel_slew_and_take_image_checkout.py``

v1.19.1
-------

* In ``auxtel/daytime_checkout/atpneumatics_checkout.py``: 
  * add slew to park position to ensure telescope is in safe range for ATAOS operation.
  * add sleep to allow mirror to arrive at commanded pressure before logging value.
  * add check that M1 arrives at pressure commanded by ATAOS after enable/disable. 
  * update unit test ``tests/test_auxtel_atpneumatics_checkout.py`` 

v1.19.0
-------

* Update pre-commit to use black 23, isort 5.12 and check-yaml 4.4.

v1.18.0
-------

* Add new ``system_wide_shutdown`` script to help shutdown the entire system.
* In ``auxtel/daytime_checkout/`` update script metadata.duration values.

v1.17.0
-------

* In ``maintel/track_target_and_take_image_gencam.py``:

  * Update ``get_schema`` method to stop deleting ``band_filter`` from the required configuration attributes.

    Previously we thought it would be ok to remove this attribute from the configuration since the generic cameras, which this script is designed to work with, don't necessarily have a filter wheel or instrument configuration.
    But this oversight doesn't take into account the fact that this Script is designed to work with the Scheduler and, for this type of Script, we can not remove any of the basic set of required parameters.
    Adding new parameters is ok though.

    If calling this script from the script queue one can simply pass in an empty string for ``band_filter``.
    But, keep in mind this one in particular is designed to work with the Scheduler.

  * Update ``track_target_and_setup_instrument`` to pass in ``az_wrap_strategy`` to slew_icrs.

  * Implement new ``tcs`` abstract property introduced in ``BaseTrackTargetAndTakeImage``.

* In ``maintel/track_target_and_take_image_comcam.py``:

  * Update ``track_target_and_setup_instrument`` and ``_handle_slew_and_change_filter`` to pass in ``az_wrap_strategy``.

  * Implement new ``tcs`` abstract property introduced in ``BaseTrackTargetAndTakeImage``.

* In ``auxtel/track_target_and_take_image.py``, update ``track_target_and_setup_instrument`` to pass ``az_wrap_strategy`` to ``atcs.slew_icrs``.

* In ``base_track_target_and_take_image.py``:

  * Add ``az_wrap_strategy`` to the script configuration.

    This allows users to specify the azimuth wrap strategy the TCS should use when slewing to a target.
    The parameter is exposed as an enumeration with all the available options.
    Users select an option by adding one of the available strings.
    When configuring the Script, the ``configure`` method will convert the string into the appropriate enumeration, calling in the ``tcs`` property to return the ``WrapStrategy`` enumeration.

  * Update ``set_metadata`` to use ``get_estimated_time_on_target`` as the script estimated duration and also to fill up all the relevant metadata information.

    This update will make sure the ``nextVisit`` event published by this script has all the relevant information needed by prompt processing.

  * Add new method ``get_estimated_time_on_target`` that returns the estimated time on target, based on the script configuration.

    Having this method allows the Script to uniformly estimate its duration in different execution stages.

  * Add new ``tcs`` abstract property to ``BaseTrackTargetAndTakeImage``, which should return the instance of the tcs class on the script.

  This change goes in the direction of supporting higher level abstraction that require calling the TCS class from within the base class.

* In ``base_track_target``, add support for azimuth wrap strategy and differential tracking.

  * Include configuration parameters to allow users to specify values for azimuth wrap strategy and differential tracking.

  * Pass those values to ``slew_icrs`` and ``slew_object`` when running the script.

v1.16.1
-------

* Fix conda recipe by adding astroplan dependency and not running pytest.

v1.16.0
-------

* Add daytime_checkout SAL scripts, executables, and tests
* Move all "prepare_for" scripts to a submodule in auxtel.
* Add new ``prepare_for/vent.py``.
* Update pre-commit configuration.
* Run ``isort`` in the entire package.

v1.15.5
-------

* Update maintel/setup_mtcs.py
  * Now put the mount and the rotator into disabled state so they can share telemetry.
  * Do the homing of the mount

v1.15.4
-------

* Add maintel/track_target_and_take_image_comcam.py with new ``TrackTargetAndTakeImageGenCam``.
* Add unit tests for ``TrackTargetAndTakeImageGenCam``

v1.15.3
-------

* `BaseScriptTestCase` fix a potential unbound local variable error in ``check_executable``.
  This is only triggered if the process cannot be created or $PATH cannot be set, so it obscures some other problem.

v1.15.2
-------

* Update unit tests to be compatible with ts_salobj 7.2, while remaining backwards compatible.
* Remove unused dependencies, including ts_atdome, ts_atdometrajectory and ts_atmcssimulator.
* Modernize the CI Jenkinsfile.
* In ``auxtel/track_target_and_take_image.py``:
  * Use snaps instead of isolated observations when visit is standard.
  * Add a new configuration parameter "filter_suffix" to allow appending strings to the filter name.

v1.15.1
-------

* In python/lsst/ts/standardscripts/auxtel/track_target_and_take_image.py, implement new abstract method ``check_feasibility``.

* In python/lsst/ts/standardscripts/base_track_target_and_take_image.py, add new ``assert_feasibility`` abstract method to ``BaseTrackTargetAndTakeImage``, that is called before running to verify that the system is in a feasible state to execute the script.

* In python/lsst/ts/standardscripts/maintel/track_target_and_take_image_comcam.py, implement new abstract method ``assert_feasibility``.

v1.15.0
-------

* In ``BaseTrackTargetAndTakeImage``, add configuration parameter to allow specifying a camera playlist and, if specified, load it before running the script.

* In ``base_track_target_and_take_image``, improve checkpoints messages.

* In maintel/track_target_and_take_image_comcam.py implement ``load_playlist``.

* In auxtel/track_target_and_take_image, implement ``load_playlist`` method.

v1.14.3
-------

* In ``maintel/SetupMTCS``

  * fix bug that caused ``mtcs.raise_m1m3`` to start but not to complete.
  * fix ``mtcs.enable_compensation_mode`` argument.

v1.14.2
-------

* Create new script maintel/setup_mtcs.py with its associated class and unit tests.

v1.14.1
-------

* Update eups table to account for renaming of ts_ATMCSSimulator -> ts_atmcssimulator.
* Update conda recipe to improve handling python versions.

v1.14.0
-------

* Update build files to use pyproject.toml
* Update location of scripts directory
* Move scripts to python/.../data/scripts

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
* doc/conf.py: make linters happier.
* git ignore .hypothesis.
* Use pre-commit to run flake8 and maintain black formatting.
* update build files to use ``pyproject.toml``.

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
