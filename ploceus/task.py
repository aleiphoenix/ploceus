# -*- coding: utf-8 -*-
import threading
import time

from ploceus import g
from ploceus.runtime import context_manager, env



class TaskResult(object):
    """class that represents Task running result state
    """

    def __init__(self, name):
        """
        Args:
            name (str): task name, usually set by task itself
        """
        self.rv = None
        self.error = None
        self.name = name


    @property
    def failed(self):
        """indicate whether task is finished without error

        Returns:
            bool: True if failed, False if ok
        """
        return isinstance(self.error, Exception)


    @property
    def ok(self):
        """indicate whether task is finished normally

        Returns:
            bool: True if ok, False if failed
        """
        return self.error is None


    def __repr__(self):
        status = 'ok'
        if self.failed:
            status = 'failed'
        return '<#TaskResult %s, %s>' % (self.name, status)


class Task(object):
    """function marked as a ``Task'' object
    """

    func = None
    ssh_user = None
    name = None
    local_mode = False

    def __init__(self, func, ssh_user=None, *args, **options):
        """create a ``Task'' object, register it to global store
        """
        def new_func(*_args, **_kwargs):
            rv = func(*_args, **_kwargs)
            return rv

        new_func.__name__ = func.__name__
        new_func.__module__ = func.__module__

        self.wrapped = func
        self.func = new_func
        self.ssh_user = ssh_user
        if options.get('local_mode'):
            self.local_mode = True

        module = func.__module__
        if module.lower() == 'ploceusfile':
            module = ''
        name = func.__name__
        if module:
            name = '%s.%s' % (module, name)
        self.name = name

        g.add_task(self)


    def __repr__(self):
        return '<ploceus.task.Task %s>' % self.name


    def __str__(self):
        return '<ploceus.task.Task %s>' % self.name


    def run(self, extra_vars, **kwargs):
        """wrapper, execute task against single host

        Args:
            extra_vars (dict): additional variable will be inserted into context
            **kwargs (dict): keyword arguments pass to decorated function

        Returns:
            TaskResult: running result
        """
        rv = TaskResult(self.name)
        try:
            _ = self._run(extra_vars, **kwargs)
            rv.rv = _
        except Exception as e:
            import traceback
            traceback.print_exc()
            rv.error = e
            if env.break_on_error:
                raise
        return rv


    def _run(self, extra_vars, **kwargs):
        """wrapper, execute task against single host

        Args:
            extra_vars (dict): additional variable will be inserted into context
            **kwargs (dict): keyword arguments pass to decorated function

        Returns:
            return value of decorated function
        """
        context = context_manager.get_context()

        # TODO: mask dangers context variables
        extra_vars = extra_vars or {}
        context['extra_vars'] = extra_vars

        for f in env.pre_task_hooks:
            if callable(f):
                f(context)

        rv = self.func(**kwargs)

        for f in env.post_task_hooks:
            if callable(f):
                f(context)

        return rv

    def __call__(self, *args, **kwargs):
        return self.func(*args, **kwargs)
