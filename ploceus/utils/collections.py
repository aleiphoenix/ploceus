# -*- coding: utf-8 -*-
import threading

class ScopedRegistry(object):
    """A Registry that can store one or multiple instances of a single
    class on the basis of a "scope" function.

    The object implements ``__call__`` as the "getter", so by
    calling ``myregistry()`` the contained object is returned
    for the current scope.

    :param createfunc:
      a callable that returns a new object to be placed in the registry

    :param scopefunc:
      a callable that will return a key to store/retrieve an object.
    """

    def __init__(self, createfunc, scopefunc):
        """Construct a new :class:`.ScopedRegistry`.

        :param createfunc:  A creation function that will generate
          a new value for the current scope, if none is present.

        :param scopefunc:  A function that returns a hashable
          token representing the current scope (such as, current
          thread identifier).

        """
        self.createfunc = createfunc
        self.scopefunc = scopefunc
        self.registry = {}

    def __call__(self):
        key = self.scopefunc()
        try:
            return self.registry[key]
        except KeyError:
            return self.registry.setdefault(key, self.createfunc())

    def has(self):
        """Return True if an object is present in the current scope."""

        return self.scopefunc() in self.registry

    def set(self, obj):
        """Set the value for the current scope."""

        self.registry[self.scopefunc()] = obj

    def clear(self):
        """Clear the current scope, if any."""

        try:
            del self.registry[self.scopefunc()]
        except KeyError:
            pass


class ThreadLocalRegistry(ScopedRegistry):
    """A :class:`.ScopedRegistry` that uses a ``threading.local()``
    variable for storage.

    """

    def __init__(self, createfunc):
        self.createfunc = createfunc
        self.registry = threading.local()

    def __call__(self):
        try:
            return self.registry.value
        except AttributeError:
            val = self.registry.value = self.createfunc()
            return val

    def has(self):
        return hasattr(self.registry, "value")

    def set(self, obj):
        self.registry.value = obj

    def clear(self):
        try:
            del self.registry.value
        except AttributeError:
            pass
