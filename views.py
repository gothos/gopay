# -*- coding: utf-8 -*-
# vim: tabstop=4 expandtab shiftwidth=4 softtabstop=4

from django.db import transaction
from django.http import HttpResponse

from .decorators import GPSettings


@transaction.atomic
def notify(request):
    GPSettings.tx_callback(request)
    return HttpResponse('ACK', content_type="text/plain")
