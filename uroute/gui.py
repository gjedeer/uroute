import logging
from collections import namedtuple

import gi

from uroute.url import extract_url
from uroute.util import listify

gi.require_version('Gdk', '3.0')
gi.require_version('Gtk', '3.0')
gi.require_version('Notify', '0.7')
from gi.repository import Gdk, GdkPixbuf, Gtk, Notify, Pango  # noqa E402

log = logging.getLogger(__name__)

NotificationAction = namedtuple(
    'NotificationAction', ('id', 'label', 'callback', 'user_data'),
)


def get_clipboard_url():
    clipboard = getattr(get_clipboard_url, '_clipboard', None)
    if clipboard is None:
        clipboard = Gtk.Clipboard.get(Gdk.SELECTION_CLIPBOARD)
        get_clipboard_url._clipboard = clipboard
    contents = clipboard.wait_for_text()
    return extract_url(contents)


def notify(
    title, msg, icon='dialog-info', timeout=Notify.EXPIRES_DEFAULT,
    actions=None,
):
    if not Notify.is_initted():
        Notify.init('uroute')

    notification = Notify.Notification.new(title, msg, icon=icon)
    notification.set_timeout(timeout)

    for action in listify(actions):
        notification.add_action(
            action.id, action.label, action.callback, action.user_data,
        )

    notification.show()
    return notification


class UrouteGui(Gtk.Window):
    def __init__(self, uroute):
        super(UrouteGui, self).__init__()
        self.uroute = uroute
        self.command = None
        self._build_ui()
        self.set_url(self.uroute.url)
        self._check_url()

    def run(self):
        self.show_all()
        self._check_default_browser()

        Notify.init('uroute')
        Gtk.main()

        if Notify.is_initted():
            Notify.uninit()

        return self.command

    @property
    def url(self):
        return self.url_entry.get_text()

    def set_url(self, url=None):
        if not url and not isinstance(url, str):
            url = ''

        self.url_entry.set_text(url)
        return url

    def _check_default_browser(self):
        if self.uroute.config.read_bool('ask_default_browser'):
            def set_default_browser(notif, action, user_data):
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

            def dont_set_default_browser(notif, action, user_data):
                log.debug("Don't set as default browser")
                notif.close()
                # Don't ask again
                self.uroute.config.write_bool('ask_default_browser', 'no')

            self._default_browser_notif = notify(
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
            )

    def _check_url(self):
        if not self.url \
                and self.uroute.config.read_bool('read_url_from_clipboard'):
            clipboard_url = get_clipboard_url()
            if clipboard_url:
                self.set_url(clipboard_url)
                notify('Using URL from clipboard', clipboard_url)

    def _build_ui(self):
        # Init main window
        self.set_title('Uroute - Link Dispatcher')
        self.set_border_width(10)
        self.set_default_size(860, 600)
        self.connect('destroy', self._on_cancel_clicked)
        self.connect('key-press-event', self._on_key_pressed)

        vbox = Gtk.VBox(spacing=6)
        self.add(vbox)

        mono = Pango.FontDescription('monospace')
        self.url_entry = Gtk.Entry()
        self.url_entry.modify_font(mono)
        self.command_entry = Gtk.Entry()
        self.command_entry.modify_font(mono)

        vbox.pack_start(self.url_entry, False, False, 0)
        vbox.pack_start(self._build_browser_buttons(), True, True, 0)
        vbox.pack_start(self.command_entry, False, False, 0)
        vbox.pack_start(self._build_button_toolbar(), False, False, 0)

    def _build_browser_buttons(self):
        self.browser_store = Gtk.ListStore(GdkPixbuf.Pixbuf, str, str, object)
        iconview = Gtk.IconView.new()
        iconview.set_model(self.browser_store)
        iconview.set_pixbuf_column(0)
        iconview.set_text_column(1)
        iconview.connect('item-activated', self._on_browser_icon_activated)
        iconview.connect('selection-changed', self._on_browser_icon_selected)

        default_itr = None
        default_program = self.uroute.get_program()

        for i, program in enumerate(self.uroute.programs.values()):
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
            iconview.select_path(self.browser_store.get_path(default_itr))
            self._on_browser_icon_selected(iconview)

        scroll = Gtk.ScrolledWindow()
        scroll.add(iconview)
        return scroll

    def _load_program_icon(self, program):
        icon = None
        if program.icon:
            icon = Gtk.Image.new_from_file(program.icon).get_pixbuf()
            if icon.get_width() > 64 or icon.get_height() > 64:
                icon = icon.scale_simple(
                    64, 64, GdkPixbuf.InterpType.BILINEAR,
                )
            if icon is None:
                log.warn('Unable to load icon from %s', program.icon)

        if icon is None:
            icon = Gtk.IconTheme.get_default().load_icon(
                'help-about', 64, 0,
            )
        return icon

    def _build_button_toolbar(self):
        hbox = Gtk.Box(spacing=6)

        button = Gtk.Button.new_with_mnemonic('Run')
        button.connect('clicked', self._on_run_clicked)
        hbox.pack_end(button, False, False, 0)

        button = Gtk.Button.new_with_label('Cancel')
        button.connect('clicked', self._on_cancel_clicked)
        hbox.pack_end(button, False, False, 0)

        return hbox

    def _on_browser_icon_activated(self, iconview, path):
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

    def _on_run_clicked(self, _button):
        self.command = self.command_entry.get_text()
        self.uroute.url = self.url

        log.debug('Command: %r, URL: %r', self.command, self.uroute.url)

        self.hide()
        Gtk.main_quit()

    def _on_key_pressed(self, wnd, event):
        if event.keyval == Gdk.KEY_Escape:
            self._on_cancel_clicked(None)
        if event.keyval == Gdk.KEY_Return:
            self._on_run_clicked(None)
