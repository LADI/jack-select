"""A convenience class for a GTK 3 system tray indicator."""

from pkg_resources import resource_filename

import gi
gi.require_version('Gtk', '3.0')  # noqa
from gi.repository import Gtk
from gi.repository.GdkPixbuf import Pixbuf


class Indicator:
    """This class defines a standard GTK3 system tray indicator.

    Class Indicator can be easily reused in any other project.

    """
    def __init__(self, icon, title=None):
        """Create indicator icon and add menu.

        Args:
          icon (str): path to initial icon that will be shown on system panel

        """
        self._icon_cache = {}
        self.icon = Gtk.StatusIcon.new_from_pixbuf(self._get_icon(icon))
        self.menu = Gtk.Menu()
        self.icon.connect('activate', self.on_popup_menu_open)
        self.icon.connect('popup-menu', self.on_popup_menu_open)

        if title:
            self.icon.set_title(title)

    def _get_icon(self, icon):
        """Return icon from package as GdkPixbuf.Pixbuf.

        Extracts the image from package to a file, stores it in the icon cache
        if it's not in there yet and returns it. Otherwise just returns the
        image stored in the cache.

        """
        if icon not in self._icon_cache:
            filename = resource_filename(__name__, "images/%s" % icon)
            self._icon_cache[icon] = Pixbuf.new_from_file(filename)

        return self._icon_cache[icon]

    def set_icon(self, icon):
        """Set new icon in system tray.

        Args:
          icon (str): path to file with new icon

        """
        self.icon.set_from_pixbuf(self._get_icon(icon))

    def set_tooltip(self, callback):
        self.icon.set_has_tooltip(True)
        self.icon.connect("query-tooltip", callback)

    def clear_menu(self):
        """Clear all entries from the main menu."""
        self.menu = Gtk.Menu()

    def add_menu_item(self, command=None, title=None, icon=None, active=True,
                      data=None):
        """Add mouse right click menu item.

        Args:
          command (callable): function that will be called after left mouse
          click on title
          title (str): label that will be shown in menu
          icon (str): name of icon stored in application package
          active (bool): whether the menu entry can be activated (default: True)
          data (obj): arbitrary daat to associate with the menu entry

        """
        if icon:
            m_item = Gtk.ImageMenuItem(title)
            image = Gtk.Image.new_from_pixbuf(self._get_icon(icon))
            m_item.set_image(image)
        else:
            m_item = Gtk.MenuItem()
            m_item.set_label(title)

        if command:
            m_item.connect('activate', command)

        m_item.set_sensitive(active)
        m_item.data = data
        self.menu.append(m_item)
        return m_item

    def add_separator(self):
        """Add separator between labels in the popup menu."""
        m_item = Gtk.SeparatorMenuItem()
        self.menu.append(m_item)
        self.menu.show_all()

    def on_popup_menu_open(self, widget=None, button=None, *args):
        """Some action requested opening the popup menu."""
        self.menu.popup(None, None, Gtk.StatusIcon.position_menu,
                        widget or self.icon, button or 1,
                        Gtk.get_current_event_time())

    def on_popup_menu_close(self, widget=None, button=None, *args):
        """Some action requested closing the popup menu."""
        self.menu.popdown()
