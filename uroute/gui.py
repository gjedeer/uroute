"""Everything GUI-related."""

import logging
from collections import namedtuple

import gi

from uroute.url import extract_url
from uroute.util import listify

gi.require_version('Gdk', '3.0')
gi.require_version('Gtk', '3.0')
gi.require_version('Notify', '0.7')
# pylint: disable=wrong-import-order,wrong-import-position
from gi.repository import Gdk, GdkPixbuf, GLib, Gtk, Notify, Pango

log = logging.getLogger(__name__)

NotificationAction = namedtuple(
    'NotificationAction', ('id', 'label', 'callback', 'user_data'),
)


def get_clipboard_url():
    """Returns URL from clipboard content, or `None`."""
    clipboard = getattr(get_clipboard_url, '_clipboard', None)
    if clipboard is None:
        clipboard = Gtk.Clipboard.get(Gdk.SELECTION_CLIPBOARD)
        # pylint: disable=protected-access
        get_clipboard_url._clipboard = clipboard
    contents = clipboard.wait_for_text()
    if contents:
        return extract_url(contents)
    return None


def notify(  # pylint: disable=too-many-arguments
    title, msg, icon='dialog-information', timeout=Notify.EXPIRES_DEFAULT,
    actions=None, transient=False, urgency=Notify.Urgency.NORMAL,
):
    if not Notify.is_initted():
        Notify.init('uroute')

    notification = Notify.Notification.new(title, msg, icon=icon)
    notification.set_timeout(timeout)
    notification.set_urgency(urgency)

    if transient:
        notification.set_hint_byte('transient', 1)

    for action in listify(actions):
        notification.add_action(
            action.id, action.label, action.callback, action.user_data,
        )

    notification.show()
    return notification


class UrouteGui(Gtk.Window):  # pylint: disable=too-many-instance-attributes
    """
    Constructs main GTK GUI and hooks events to `uroute.core.Uroute`
    functionality.
    """

    def __init__(self, uroute):
        super().__init__()
        self.uroute = uroute
        self.command = None
        self.orig_url = None

        self._build_ui()

    def run(self, url):
        self.set_url(url)
        self._check_clipboard_url()
        self.show_all()
        self._check_default_browser()

        Notify.init('uroute')
        Gtk.main()

        if Notify.is_initted():
            Notify.uninit()

        return (self.command, self.url)

    @property
    def url(self):
        return self.url_entry.get_text()

    def set_url(self, url, clean=True):
        """Sets the given URL in the GUI field, after cleaning it."""
        self.orig_url = None

        if not url and not isinstance(url, str):
            url = ''

        if url and clean:
            cleaned_url = self.uroute.clean_url(url)
            if cleaned_url != url:
                self.orig_url = url
                url = cleaned_url

        if self.orig_url:
            self.clean_url_btn.hide()
            self.restore_url_btn.show()
            escaped_orig = GLib.markup_escape_text(self.orig_url)
            self.restore_url_btn.set_tooltip_markup(
                f'Restore original URL: <tt>{escaped_orig}</tt>',
            )
        else:
            self.clean_url_btn.show()
            self.restore_url_btn.hide()

        self.url_entry.set_text(url)
        return url

    # UTILITY METHODS #
    def _check_default_browser(self):
        if self.uroute.config.read_bool('ask_default_browser'):
            def set_default_browser(notif, _action, _user_data):
                notif.close()
                if self.uroute.set_as_default_browser():
                    notify(
                        'Default browser set',
                        'Uroute is now configured as your default browser.',
                    )
                    # Don't ask again
                    self.uroute.config.write_bool('ask_default_browser', 'no')
                else:
                    notify(
                        'Unable to configure Uroute as your default browser',
                        'Please see the application logs for more '
                        'information.',
                        icon='dialog-error',
                    )

            def dont_set_default_browser(notif, _action, _user_data):
                log.debug("Don't set as default browser")
                notif.close()
                # Don't ask again
                self.uroute.config.write_bool('ask_default_browser', 'no')

            notify(
                'Set as default browser?',
                'Do you want to set Uroute as your default browser?',
                icon='dialog-question',
                actions=[
                    NotificationAction(
                        'default-browser-yes', 'Yes', set_default_browser,
                        None,
                    ),
                    NotificationAction(
                        'default-browser-no', 'No', dont_set_default_browser,
                        None,
                    ),
                ],
                urgency=Notify.Urgency.CRITICAL,
            )

    def _check_clipboard_url(self):
        if not self.url \
                and self.uroute.config.read_bool('read_url_from_clipboard'):
            clipboard_url = get_clipboard_url()
            if clipboard_url:
                self.set_url(clipboard_url)
                notify(
                    'Using URL from clipboard', clipboard_url, transient=True,
                )

    def _load_program_icon(self, program):
        icon = None
        if program.icon:
            icon = Gtk.Image.new_from_file(program.icon).get_pixbuf()
            if icon is None:
                log.warning('Unable to load icon from %s', program.icon)
            else:
                if icon.get_width() > 64 or icon.get_height() > 64:
                    icon = icon.scale_simple(
                        64, 64, GdkPixbuf.InterpType.BILINEAR,
                    )

        if icon is None:
            icon = Gtk.IconTheme.get_default().load_icon(
                'help-about', 64, 0,
            )
        return icon

    # UI BUILDING METHODS #
    def _build_ui(self):
        # Init main window
        self.set_title('Uroute - Link Dispatcher')
        self.set_border_width(10)
        self.set_default_size(860, 600)
        self.connect('show', self._on_window_show)
        self.connect('destroy', self._on_cancel_clicked)
        self.connect('key-press-event', self._on_key_pressed)

        vbox = Gtk.VBox(spacing=6)
        self.add(vbox)

        # The command entry needs to exist before creating the browser
        # buttons, so we create it first.
        command_hbox = self._build_command_hbox()

        vbox.pack_start(self._build_url_entry_hbox(), False, False, 0)
        vbox.pack_start(self._build_browser_buttons(), True, True, 0)
        vbox.pack_start(command_hbox, False, False, 0)
        vbox.pack_start(self._build_button_toolbar(), False, False, 0)

    def _build_url_entry_hbox(self):
        url_entry_hbox = Gtk.HBox()

        # pylint: disable=attribute-defined-outside-init
        self.url_entry = Gtk.Entry()
        self.url_entry.modify_font(Pango.FontDescription('monospace'))

        # pylint: disable=attribute-defined-outside-init
        self.clean_url_btn = Gtk.Button.new_with_label('Clean')
        self.clean_url_btn.connect('clicked', self._on_clean_url_clicked)
        # pylint: disable=attribute-defined-outside-init
        self.restore_url_btn = Gtk.Button.new_with_label('Restore')
        self.restore_url_btn.connect('clicked', self._on_restore_orig_url)

        url_entry_hbox.pack_start(self.url_entry, True, True, 5)
        url_entry_hbox.pack_start(self.clean_url_btn, False, False, 0)
        url_entry_hbox.pack_start(self.restore_url_btn, False, False, 0)

        return url_entry_hbox

    def _build_browser_buttons(self):
        # pylint: disable=attribute-defined-outside-init
        self.browser_store = Gtk.ListStore(GdkPixbuf.Pixbuf, str, str, object)
        # pylint: disable=attribute-defined-outside-init
        self.iconview = Gtk.IconView.new()
        self.iconview.set_model(self.browser_store)
        self.iconview.set_pixbuf_column(0)
        self.iconview.set_text_column(1)
        self.iconview.connect('item-activated', self._on_browser_icon_activated)
        self.iconview.connect('selection-changed', self._on_browser_icon_selected)

        default_itr = None
        default_program = self.uroute.get_program()

        for program in self.uroute.programs.values():
            itr = self.browser_store.append([
                self._load_program_icon(program), program.name,
                program.command, program,
            ])
            if program is default_program:
                log.debug(
                    'Selecting default program: %r',
                    self.browser_store.get_value(itr, 2),
                )
                default_itr = itr

        if default_itr:
            self.iconview.select_path(self.browser_store.get_path(default_itr))
            self._on_browser_icon_selected(self.iconview)

        scroll = Gtk.ScrolledWindow()
        scroll.add(self.iconview)
        return scroll

    def _build_command_hbox(self):
        # pylint: disable=attribute-defined-outside-init
        self.command_entry = Gtk.Entry()
        self.command_entry.modify_font(Pango.FontDescription('monospace'))
        return self.command_entry

    def _build_button_toolbar(self):
        hbox = Gtk.Box(spacing=6)

        button = Gtk.Button.new_with_mnemonic('Run')
        button.connect('clicked', self._on_run_clicked)
        hbox.pack_end(button, False, False, 0)

        button = Gtk.Button.new_with_label('Cancel')
        button.connect('clicked', self._on_cancel_clicked)
        hbox.pack_end(button, False, False, 0)

        return hbox

    # EVENT HANDLERS #
    def _on_browser_icon_activated(self, _iconview, _path):
        self._on_run_clicked(None)

    def _on_browser_icon_selected(self, iconview):
        model = iconview.get_model()
        paths = iconview.get_selected_items()
        if not paths:
            log.debug('No browser selected.')
            return
        sel_iter = model.get_iter(paths[0])

        self.command_entry.set_text(model.get_value(sel_iter, 2))

    def _on_cancel_clicked(self, _button):
        self.command = None
        self.hide()
        Gtk.main_quit()

    def _on_clean_url_clicked(self, _button):
        self.set_url(self.url, clean=True)

    def _on_restore_orig_url(self, _button):
        self.set_url(self.orig_url, clean=False)

    def _on_run_clicked(self, _button):
        self.command = self.command_entry.get_text()
        self.hide()
        Gtk.main_quit()

    def _on_key_pressed(self, _wnd, event):
        if event.keyval == Gdk.KEY_Escape:
            self._on_cancel_clicked(None)
        if event.keyval == Gdk.KEY_Return:
            self._on_run_clicked(None)

    def _on_window_show(self, _window):
        # Hack required because gtk
        self.clean_url_btn.set_visible(not self.orig_url)
        self.restore_url_btn.set_visible(bool(self.orig_url))
        # Set focus to the browser buttons area instead of the URL entry
        self.iconview.grab_focus()
