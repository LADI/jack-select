ChangeLog
=========


1.2.0 (2019-04-17)
------------------

* Detect changes in connected ALSA devices and enable/disable preset,
  which use these devices in the menu.
* Added command line option ``-a``, ``--no-alsa-monitor`` to disable
  ALSA device monitoring and filtering.
* Made some logging improvements.


1.1.2 (2018-09-15)
------------------

* Display underscores in configuration preset names as spaces in menu.


1.1.1 (2018-09-04)
------------------

* Exit cleanly without traceback on INT signal.
* Correctly parse QjackCtl.conf having only one default preset.


1.1.0 (2016-12-25)
------------------

* Add command line option to activate default JACK configuration preset.


1.0 (2016-05-30)
----------------

* First stable release.
