# -*- coding: utf-8 -*-
"""I2P proxy."""

import base64
import getpass
import io
import os
import platform
import pprint
import re
import shlex
import shutil
import subprocess
import sys
import traceback
import urllib.parse
import warnings

import requests
import selenium
import stem.util.term

import darc.typing as typing
from darc.const import DARC_USER, DEBUG, PATH_DB, QUEUE_REQUESTS, VERBOSE
from darc.error import I2PBootstrapFailed, UnsupportedPlatform, render_error
from darc.link import Link, parse_link

__all__ = ['I2P_REQUESTS_PROXY', 'I2P_SELENIUM_PROXY']

# I2P args
I2P_ARGS = shlex.split(os.getenv('I2P_ARGS', ''))

# bootstrap wait
BS_WAIT = float(os.getenv('I2P_WAIT', '90'))

# I2P port
I2P_PORT = os.getenv('I2P_PORT', '4444')

# I2P bootstrap retry
I2P_RETRY = int(os.getenv('I2P_RETRY', '3'))

# proxy
I2P_REQUESTS_PROXY = {
    # c.f. https://stackoverflow.com/a/42972942
    'http':  f'http://localhost:{I2P_PORT}',
    'https': f'http://localhost:{I2P_PORT}'
}
I2P_SELENIUM_PROXY = selenium.webdriver.Proxy()
I2P_SELENIUM_PROXY.proxyType = selenium.webdriver.common.proxy.ProxyType.MANUAL
I2P_SELENIUM_PROXY.http_proxy = f'http://localhost:{I2P_PORT}'
I2P_SELENIUM_PROXY.ssl_proxy = f'http://localhost:{I2P_PORT}'

# I2P bootstrapped flag
_I2P_BS_FLAG = False
# I2P daemon process
_I2P_PROC = None
# I2P bootstrap args
_unsupported = False
if getpass.getuser() == 'root':
    _system = platform.system()
    if _system in ['Linux', 'Darwin']:
        _I2P_ARGS = ['su', '-', DARC_USER, 'i2prouter', 'start']
    else:
        _unsupported = True
        _I2P_ARGS = list()
else:
    _I2P_ARGS = ['i2prouter', 'start']
_I2P_ARGS.extend(I2P_ARGS)

if VERBOSE:
    print(stem.util.term.format('-*- I2P PROXY -*-',
                                stem.util.term.Color.MAGENTA))  # pylint: disable=no-member
    if _unsupported:
        print(stem.util.term.format(f'unsupported system: {platform.system()}',
                                    stem.util.term.Color.RED))  # pylint: disable=no-member
    else:
        print(render_error(pprint.pformat(_I2P_ARGS), stem.util.term.Color.MAGENTA))  # pylint: disable=no-member
    print(stem.util.term.format('-' * shutil.get_terminal_size().columns,
                                stem.util.term.Color.MAGENTA))  # pylint: disable=no-member


def _i2p_bootstrap():
    """I2P bootstrap."""
    global _I2P_BS_FLAG, _I2P_PROC

    # launch I2P process
    _I2P_PROC = subprocess.Popen(
        _I2P_ARGS, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
    )

    try:
        stdout, stderr = _I2P_PROC.communicate(timeout=BS_WAIT)
    except subprocess.TimeoutExpired as error:
        stdout, stderr = error.stdout, error.stderr
    if VERBOSE:
        if stdout is not None:
            print(render_error(stdout, stem.util.term.Color.BLUE))  # pylint: disable=no-member
    if stderr is not None:
        print(render_error(stderr, stem.util.term.Color.RED))  # pylint: disable=no-member

    returncode = _I2P_PROC.returncode
    if returncode is not None and returncode != 0:
        raise subprocess.CalledProcessError(returncode, _I2P_ARGS,
                                            _I2P_PROC.stdout,
                                            _I2P_PROC.stderr)

    # update flag
    _I2P_BS_FLAG = True


def i2p_bootstrap():
    """Bootstrap wrapper for I2P."""
    if _unsupported:
        raise UnsupportedPlatform(f'unsupported system: {platform.system()}')

    # don't re-bootstrap
    if _I2P_BS_FLAG:
        return

    print(stem.util.term.format('-*- I2P Bootstrap -*-',
                                stem.util.term.Color.MAGENTA))  # pylint: disable=no-member
    for _ in range(I2P_RETRY+1):
        try:
            _i2p_bootstrap()
            break
        except Exception as error:
            if DEBUG:
                message = f'[Error bootstraping I2P proxy]' + os.linesep + traceback.format_exc()
                print(render_error(message, stem.util.term.Color.RED), end='', file=sys.stderr)  # pylint: disable=no-member

            warning = warnings.formatwarning(error, I2PBootstrapFailed, __file__, 123, 'i2p_bootstrap()')
            print(render_error(warning, stem.util.term.Color.YELLOW), end='', file=sys.stderr)  # pylint: disable=no-member
    print(stem.util.term.format('-' * shutil.get_terminal_size().columns,
                                stem.util.term.Color.MAGENTA))  # pylint: disable=no-member


def get_hosts(link: Link) -> typing.Optional[typing.Dict[str, typing.Union[str, typing.ByteString]]]:  # pylint: disable=inconsistent-return-statements
    """Read ``hosts.txt``."""
    path = os.path.join(link.base, 'hosts.txt')
    if not os.path.isfile(path):
        return
    with open(path, 'rb') as file:
        content = file.read()
    data = dict(
        path=os.path.relpath(path, PATH_DB),
        data=base64.b64encode(content).decode(),
    )
    return data


def has_i2p(link_pool: typing.Set[str]) -> bool:
    """Check if contain I2P links."""
    for link in link_pool:
        # <scheme>://<netloc>/<path>;<params>?<query>#<fragment>
        parse = urllib.parse.urlparse(link)
        host = parse.netloc or parse.hostname

        if re.fullmatch(r'.*?\.i2p', host):
            return True
        # c.f. https://geti2p.net/en/docs/api/i2ptunnel
        if host in ['127.0.0.1:7657', '127.0.0.1:7658', '127.0.0.1:6668', '127.0.0.1:8998', '127.0.0.1:7659', '127.0.0.1:7660',  # pylint: disable=line-too-long
                    'localhost:7657', 'localhost:7658', 'localhost:6668', 'localhost:8998', 'localhost:7659', 'localhost:7660']:  # pylint: disable=line-too-long
            return True
    return False


def has_hosts(link: Link) -> typing.Optional[str]:
    """Check if hosts.txt already exists."""
    # <proxy>/<scheme>/<host>/hosts.txt
    path = os.path.join(link.base, 'hosts.txt')
    return path if os.path.isfile(path) else None


def save_hosts(link: Link, text: str) -> str:
    """Save `hosts.txt`."""
    path = os.path.join(link.base, 'hosts.txt')

    root = os.path.split(path)[0]
    os.makedirs(root, exist_ok=True)

    with open(path, 'w') as file:
        print(f'# {link.url}', file=file)
        file.write(text)
    return path


def read_hosts(text: typing.Iterable[str]) -> typing.Iterable[str]:
    """Read `hosts.txt`."""
    for line in filter(lambda s: s.strip(), text):
        if line.startswith('#'):
            continue
        yield line.split('=')[0]


def fetch_hosts(link: Link):
    """Fetch `hosts.txt`."""
    hosts_path = has_hosts(link)
    if hosts_path is not None:

        print(stem.util.term.format(f'[HOSTS] Cached {link.url}',
                                    stem.util.term.Color.YELLOW))  # pylint: disable=no-member
        hosts_file = open(hosts_path)

    else:

        from darc.requests import i2p_session  # pylint: disable=import-outside-toplevel

        hosts_link = parse_link(urllib.parse.urljoin(link.url, '/hosts.txt'))
        print(f'[HOSTS] Subscribing {hosts_link.url}')

        with i2p_session() as session:
            try:
                response = session.get(hosts_link.url)
            except requests.RequestException as error:
                print(render_error(f'[HOSTS] Failed on {hosts_link.url} <{error}>',
                                   stem.util.term.Color.RED), file=sys.stderr)  # pylint: disable=no-member
                return

        if response.ok:
            save_hosts(hosts_link, response.text)
            hosts_file = io.StringIO(response.text)
        else:
            print(render_error(f'[HOSTS] Failed on {hosts_link.url} [{response.status_code}]',
                               stem.util.term.Color.RED), file=sys.stderr)  # pylint: disable=no-member
            hosts_file = io.StringIO()

        print(f'[HOSTS] Subscribed {hosts_link.url}')

    # add link to queue
    [QUEUE_REQUESTS.put(url) for url in read_hosts(hosts_file)]  # pylint: disable=expression-not-assigned
