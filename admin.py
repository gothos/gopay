# -*- coding: utf-8 -*-
# vim: tabstop=4 expandtab shiftwidth=4 softtabstop=4

from django.contrib import admin
from .models import PaymentMethod


class PaymentMethodAdmin(admin.ModelAdmin):
    list_display = ('name', 'visible', 'gopay_code')


admin.site.register(PaymentMethod, PaymentMethodAdmin)