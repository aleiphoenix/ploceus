# -*- coding: utf-8 -*-
from ploceus.context import ContextManager
from ploceus.environment import Environment


default_env = Environment()

# deprecated name
context_manager = ContextManager()
env = default_env
