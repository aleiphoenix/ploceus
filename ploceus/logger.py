# -*- coding: utf-8 -*-
import logging
import sys

from ploceus.colors import green

logger = logging.getLogger('ploceus.helper')
del logger.handlers[:]
hdl = logging.StreamHandler(sys.stderr)
hdl.setLevel(logging.INFO)
logger.addHandler(hdl)
logger.setLevel(logging.INFO)
logger.propagate = False

logger = logging.getLogger('ploceus.general')
del logger.handlers[:]
hdl = logging.StreamHandler(sys.stderr)
hdl.setLevel(logging.INFO)
hdl.setFormatter(logging.Formatter('%(levelname)s:%(name)s:%(message)s'))
logger.addHandler(hdl)
logger.setLevel(logging.INFO)
logger.propagate = False

# FIXME: avoid global
logger = logging.getLogger('ploceus.helper')


def log(message, prefix=''):
    from ploceus.runtime import context_manager

    context = context_manager.get_context()
    hostname = context.get('host_string', '')

    _ = '[%s] %s: %s' % (green(hostname), prefix, message)
    _logger = logging.getLogger('ploceus.helper')
    _logger.info(_)
