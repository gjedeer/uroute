"""Creating and managing Uroute configuraiton."""

import os
from configparser import ConfigParser

from xdg import BaseDirectory


DEFAULT_CONFIG = os.path.join(
    BaseDirectory.xdg_config_home, 'uroute', 'uroute.ini'
)


def create_initial_config(filename):
    import webbrowser  # pylint: disable=import-outside-toplevel
    config = ConfigParser()
    config['main'] = {}  # Just to make sure 'main' is added first
    default_browser = None

    # pylint: disable=protected-access
    for browser_name in webbrowser._browsers:
        if browser_name == 'firefox':
            config['program:firefox'] = {
                'name': 'Firefox',
                'command': 'firefox',
            }
            config['program:firefox-private'] = {
                'name': 'Firefox Private Window',
                'command': 'firefox --private-window',
            }
            default_browser = 'firefox-private'
        elif browser_name == 'chromium-browser':
            config['program:chromium'] = {
                'name': 'Chromium',
                'command': 'chromium-browser',
            }
            config['program:chromium-incognito'] = {
                'name': 'Chromium Incognito',
                'command': 'chromium-browser --incognito',
            }
            config['program:chromium-temp'] = {
                'name': 'Chromium Temp Profile',
                'command': 'chromium-browser --temp-profile',
            }

            if not default_browser:
                default_browser = 'chromium-incognito'

    if default_browser:
        config['main'] = {'default_program': default_browser}

    with open(filename, 'w', encoding='UTF-8') as config_file:
        config.write(config_file)


class Config(ConfigParser):
    """Uroute configuraiton."""

    def __init__(self, filename=None):
        super().__init__()

        if filename is None:
            filename = DEFAULT_CONFIG
        self.filename = filename

        if not os.path.isfile(filename):
            dirname = os.path.dirname(filename)
            if not os.path.isdir(dirname):
                os.makedirs(dirname)

            create_initial_config(filename)

        self.clear()
        self.read(filename)

        if not self.has_section('main'):
            self['main'] = {}

    def read_bool(self, setting, section='main', fallback=True):
        try:
            value = self[section].getboolean(setting, fallback=fallback)
        except ValueError:
            self[section][setting] = 'yes' if fallback else 'no'
            value = fallback

        return value

    def save(self):
        with open(self.filename, 'w', encoding='UTF-8') as config_file:
            self.write(config_file)

    def write_bool(self, setting, value, section='main'):
        self[section][setting] = value
        self.save()
