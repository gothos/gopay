# -*- coding: utf-8 -*-
# vim: tabstop=4 expandtab shiftwidth=4 softtabstop=4

from django.db import models
from django.utils.translation import ugettext as _

class PaymentMethodQuerySet(models.QuerySet):

    def available(self, **kwargs):
        return self.filter(visible=True)


class PaymentMethod(models.Model):
    """
        list of payments methods
    """
    name = models.CharField(max_length=100, verbose_name=_(u"Název"))
    visible = models.BooleanField(default=True, verbose_name=_(u"Zobrazovat"))
    sort = models.IntegerField(verbose_name=_(u"Pořadí"))
    gopay_code = models.CharField(max_length=16, verbose_name=_(u"Kód u GoPay dle 12.9 Kódy platebních metod"), null=True, blank=True)
    fee = models.DecimalField(max_digits=20, decimal_places=2, verbose_name="Poplatek", default=0)
    objects = PaymentMethodQuerySet().as_manager()

    class Meta:
        verbose_name = _(u"Platební metoda")
        verbose_name_plural = _(u"Platební metody")

    def __unicode__(self):
        return self.name