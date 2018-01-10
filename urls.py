# -*- coding: utf-8 -*-
# vim: tabstop=4 expandtab shiftwidth=4 softtabstop=4

from django.conf.urls import patterns, url

from .views import notify

urlpatterns = patterns('gopay.views',
    url(r'^notify$', notify, name='notify'),
)
