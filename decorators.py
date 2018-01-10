# -*- coding: utf-8 -*-
# vim: tabstop=4 expandtab shiftwidth=4 softtabstop=4

from django.core.exceptions import ImproperlyConfigured


class GPSettings(object):
    @staticmethod
    def tx_callback(request):
        raise ImproperlyConfigured("TX callback not defined")

    tx_model = None


def transaction_model(o):
    if not getattr(o, 'GPMeta'):
        raise ImproperlyConfigured("GPMeta must be set")
    GPSettings.tx_model = o

    return o


def transaction_callback(f):
    GPSettings.tx_callback = staticmethod(f)

    return f
