import argparse
import logging

from uroute.core import Uroute
from uroute.gui import UrouteGui

log = logging.getLogger(__name__)


def create_argument_parser():
    parser = argparse.ArgumentParser(
        description='Route URL to a configured program.',
    )

    parser.add_argument('URL', nargs='?', help='URL to route.')
    parser.add_argument(
        '--program', '-p', help='Preselect the specified program.',
    )
    parser.add_argument(
        '--version', action='store_true', help='Print version and exit.',
    )

    return parser


def main():
    options = create_argument_parser().parse_args()

    if options.version:
        from uroute.__version__ import version
        print('Uroute {}'.format(version))
        exit(0)

    ur = Uroute(preferred_prog=options.program)

    try:
        command, url = UrouteGui(ur).run(options.URL)
        log.debug('Command: %r, URL: %r', command, url)
        if command:
            ur.run(command, url)
    except Exception as error:
        log.exception(str(error))
        exit(1)


if __name__ == "__main__":
    main()
