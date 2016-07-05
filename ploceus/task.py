# -*- coding: utf-8 -*-
import threading
import time

from ploceus import g
from ploceus import exceptions
from ploceus.runtime import context_manager, env
from ploceus.ssh import SSHClient


SSH_CLIENTS = []


def append_ssh_client(client):
    global SSH_CLIENTS
    SSH_CLIENTS.append(client)


def dispose_ssh_clients():
    global SSH_CLIENTS
    for client in SSH_CLIENTS:
        client.close()


class TaskResult(object):

    def __init__(self, name):
        self.rv = None
        self.error = None
        self.name = name

    @property
    def failed(self):
        return isinstance(self.error, Exception)


    def __repr__(self):
        status = 'ok'
        if self.failed:
            status = 'failed'
        return '<#TaskResult %s, %s>' % (self.name, status)


def run_task_by_host(hostname, tasks,
                     extra_vars=None, **kwargs):
    from ploceus import g
    hosts = [hostname]
    extra_vars = extra_vars or {}

    if type(tasks) != list:
        tasks = [tasks]

    for task in tasks:
        TaskRunner.run_task_with_hosts(task, hosts,
                                       extra_vars=extra_vars,
                                       **kwargs)


def run_task_by_group(group_name, tasks,
                      extra_vars=None, parallel=False, **kwargs):
    from ploceus import g
    g.inventory.find_inventory()
    group = g.inventory.get_target_hosts(group_name)
    hosts = group['hosts']
    extra_vars = extra_vars or {}
    if 'vars' in group:
        extra_vars.update(group['vars'])

    if type(tasks) != list:
        tasks = [tasks]

    for task in tasks:
        TaskRunner.run_task_with_hosts(task, hosts,
                                       parallel=parallel,
                                       extra_vars=extra_vars,
                                       **kwargs)


class Task(object):

    def __init__(self, func, ssh_user=None):
        self.func = func
        self.ssh_user = ssh_user

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


    def run(self, hostname, extra_vars=None, *args, **kwargs):
        rv = TaskResult(self.name)
        try:
            _ = self._run(hostname, extra_vars, *args, **kwargs)
            rv.rv = _
        except Exception as e:
            import traceback
            traceback.print_exc()
            rv.error = e
            if env.break_on_error:
                raise
        return rv


    def _run(self, hostname, extra_vars, *args, **kwargs):
        context = context_manager.get_context()

        # TODO mask dangers context variables
        extra_vars = extra_vars or {}
        context['extra_vars'] = extra_vars

        # ansible like host_vars
        context['extra_vars'].update(
            g.inventory.get_target_host(hostname))

        # connect to remote host
        client = SSHClient()
        append_ssh_client(client)

        password = None
        if 'password' in kwargs:
            password = kwargs.pop('password')

        username = self.ssh_user
        if '@' in hostname:
            username, hostname = hostname.split('@', maxsplit=1)

        username = client.connect(hostname, username=username,
                                  password=password)

        # setting context
        context['sshclient'] = client
        context['host_string'] = hostname
        context['username'] = username

        for f in env.pre_task_hooks:
            if callable(f):
                f(context)

        rv = self.func(*args, **kwargs)

        for f in env.post_task_hooks:
            if callable(f):
                f(context)

        return rv

class TaskRunner(object):

    @staticmethod
    def run_task_with_hosts(task, hosts, parallel=False,
                            sleep=0, password=None, **kwargs):

        rv = {}
        if parallel:
            # TODO: return values
            rv = TaskRunner.run_task_concurrently(
                task, hosts, password=password, **kwargs)
        else:
            rv = TaskRunner.run_task_single_thread(
                task, hosts, sleep=sleep, password=password, **kwargs)

        # close all clients
        dispose_ssh_clients()
        return rv


    @staticmethod
    def run_task_single_thread(task, hosts, sleep=0, password=None, **kwargs):
        rv = {}
        if hosts is None:
            return

        for host in hosts:
            _rv = task.run(host, password=password, **kwargs)
            rv[host] = _rv
            if sleep:
                time.sleep(sleep)

        return rv

    @staticmethod
    def run_task_concurrently(task, hosts, password=None, **kwargs):
        if hosts is None:
            return

        threads = list()

        def thread_wrapper(task, host, password, **kwargs):
            try:
                task.run(host, password=password, **kwargs)
            except:
                print('error when running task: %s, host: %s, kwargs: %s' %
                      (task, host, kwargs))
                raise

        for host in hosts:

            t = threading.Thread(target=thread_wrapper,
                                 args=(task, host, password, ),
                                 kwargs=kwargs)
            t.start()
            threads.append(t)

        while True:
            for t in threads:
                if t.is_alive():
                    t.join(timeout=1)
                else:
                    threads.remove(t)
                    break

            if len(threads) == 0:
                break
