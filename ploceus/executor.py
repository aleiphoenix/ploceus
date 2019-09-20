# -*- coding: utf-8 -*-
import time

from ploceus import g
from ploceus.exceptions import ArgumentError, PloceusError
from ploceus.runtime import context_manager, env
from ploceus.ssh import SSHClient

from ploceus.logger import logger


def group_task(tasks, group, inventory=None,
               sleep=None, parallel=None,
               ssh_user=None, ssh_pwd=None,
               extra_vars=None, cli_options=None, **kwargs):
    """Programmable interface for running tasks by host groups specified
    in inventory file. This function is  intended to be used by any 3rd-party
    Python code only.

    Args:
        tasks (list[ploceus.task.Task]): task list or a single task.
        group (str): hosts group name
        inventory (str): path to inventory file/directory
        sleep (int): interval between two tasks when not in parallel mode,
            in seconds
        parallel (bool): whether run tasks in parallel fashion. ** [not
            supported yet] **
        ssh_user (str): username to use when connecting ssh, will override
            username in task's property, sshconfig and hostname
        ssh_pwd (str): password to use when connecting ssh, will override
            password in sshconfig
        extra_vars (dict): additional variables which be inserted into context
        **kwargs (dict): keyword arguments will pass to decorated function
    """
    if g.inventory.empty:
        raise ArgumentError('cannot find inventory.')
    group_hosts = g.inventory.get_target_hosts(group)
    return run_task(
        tasks, group_hosts['hosts'],
        sleep=sleep,
        parallel=parallel,
        ssh_user=ssh_user,
        ssh_pwd=ssh_pwd,
        extra_vars=extra_vars,
        cli_options=cli_options,
        **kwargs)


def run_task(tasks, hosts,
             sleep=None, parallel=None,
             ssh_user=None, ssh_pwd=None,
             extra_vars=None, cli_options=None, **kwargs):
    """Programmable interface for running tasks,
    could be used by any 3rd-party Python code or plocues itself.

    Args:
        tasks (list[ploceus.task.Task]): task list or a single task.
        hosts (list[str]): hosts FQDN name or set in ``hosts'' file.
        sleep (int): interval between two tasks when not in parallel mode,
            in seconds
        parallel (bool): whether run tasks in parallel fashion. ** [not
            supported yet] **
        ssh_user (str): username to use when connecting ssh, will override
            username in task's property, sshconfig and hostname
        ssh_pwd (str): password to use when connecting ssh, will override
            password in sshconfig
        extra_vars (dict): additional variables which be inserted into context
        **kwargs (dict): keyword arguments will pass to decorated function
    """
    # TODO:
    if parallel:
        raise PloceusError('parallel mode no implemented yet.')

    rv = {}
    username = None
    password = None

    if not isinstance(hosts, list):
        raise RuntimeError('hosts should be a list')

    if type(tasks) != list:
        tasks = [tasks]

    if ssh_user:
        username = ssh_user
    if ssh_pwd:
        password = ssh_pwd

    if not cli_options:
        cli_options = {}

    # FIXME: 定义钩子参数
    for f in env.setup_hooks:
        f(cli_options=cli_options)

    remote_tasks = filter(lambda x: x.local_mode is False, tasks)
    local_tasks = filter(lambda x: x.local_mode is True, tasks)

    sshclients = []

    for task in remote_tasks:
        for host in hosts:
            hostname = host

            # setting context
            context = context_manager.get_context()
            context['password'] = password
            context['username'] = username
            context['host_string'] = hostname

            sshclient = SSHClient()
            context.sshclient = sshclient
            sshclients.append(sshclient)

            if not username:
                username = task.ssh_user

            if '@' in hostname:
                _, hostname = hostname.split('@', maxsplit=1)
                if not username:
                    username = _

            logger.debug('username: {}'.format(username))
            logger.debug('task.ssh_user: {}'.format(task.ssh_user))

            # ansible like host_vars
            extra_vars = extra_vars or {}
            extra_vars.update(
                g.inventory.get_target_host(hostname))

            rv[hostname] = task.run(extra_vars=extra_vars, **kwargs)

        if sleep:
            time.sleep(sleep)

    for task in local_tasks:
        hostname = '_local'  # FIXME: temporary fix
        context = context_manager.get_context()
        context['cwd'] = env.cwd
        context['host_string'] = hostname
        context['password'] = None
        context['username'] = None
        rv[hostname] = task.run(extra_vars={}, **kwargs)

    # FIXME: May have nested call in tasks, dispose connection
    # after all tasks have been executed. A try-catch-finally will be better
    for c in sshclients:
        c.close()

    return rv
