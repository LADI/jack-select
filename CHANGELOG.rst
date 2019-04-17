ChangeLog
=========


1.2.0 (2019-04-17)
------------------

* Now detects changes in connected ALSA devices and enables/disables
  menu entries for presets, which use these devices.
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
