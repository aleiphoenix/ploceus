# -*- coding: utf-8 -*-
from contextlib import contextmanager
import os
import warnings


from ploceus.utils.collections import ThreadLocalRegistry
from ploceus.utils.local import LocalStack


class Scope(dict):
    """
    top level scope for internal usage

    It is intented for tracking for TaskExecutor context
    like a stack for nested situation.
    """
    def __init__(self):
        self.stack = LocalStack()

    @property
    def top(self):
        return self.stack.top

    def push(self, v):
        return self.stack.push(v)

    def pop(self):
        return self.stack.pop()


class Context(dict):
    """
    context for single task execution
    """

    def __init__(self):
        self.sshclient = None

    def get_client(self):
        if not self.sshclient._connected:

            username = self['username']
            hostname = self['host_string']
            password = self['password']

            from ploceus.runtime import env
            gateway = env.gateway_settings.get(hostname)

            username = self.sshclient.connect(
                hostname,
                username=username,
                password=password,
                gateway=gateway)

            self['username'] = username

        return self.sshclient


def get_current_scope():
    """
    magic GLOBAL STATIC function for get current scope,
    using ThreadingLocal

    It's even valid to use in a multi-threading context.

    t1 = threading.Thread(
        target=run_task, args=(task1, ['localhost', 'remote'],))
    t2 = threading.Thread(
        target=run_task, args=(task1, ['localhost', 'remote'],))
    t1.start()
    t2.start()
    t1.join()
    t2.join()
    """
    return scope_registry()


# proxy storage for Scope instances...
# intented for multi-threading usage, so ThreadingLocal()
scope_registry = ThreadLocalRegistry(lambda: Scope())


def new_context():
    rv = Context()
    rv['extra_vars'] = {}
    return rv


class ContextManager(object):
    """
    Somehow deprecated usage, for compatibility purpose

    context_manager.get_context()
    """
    def get_context(self):
        """
        get task execution context

        context is now in "/scope_stack/task_ident/..."
        """
        rv = get_current_scope().top
        if rv is None:
            msg = ('should not using any scope/context-award function'
                   'in bare python code')
            warnings.warn(msg)
            return Context()
        return rv


def cd(path):

    from ploceus.runtime import context_manager
    context = context_manager.get_context()

    path = path.replace(' ', '\ ')
    if 'cwd' in context and \
       not path.startswith('/') and \
       not path.startswith('~'):
        new_cwd = os.path.join(context['cwd'], path)
    else:
        new_cwd = path

    return _setenv('cwd', new_cwd)


@contextmanager
def _setenv(name, value):

    from ploceus.runtime import context_manager
    context = context_manager.get_context()

    previous = context.get(name)
    context[name] = value
    err = None
    try:
        yield
    except Exception as e:
        err = e

    if previous:
        context[name] = previous
    else:
        context[name] = None

    if err is not None:
        raise err
