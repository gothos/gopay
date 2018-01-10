# -*- coding: utf-8 -*-
# vim: tabstop=4 expandtab shiftwidth=4 softtabstop=4

from django.db.models.query import QuerySet
from django.db.models import Manager


class ForUpdateQuerySet(QuerySet):
    def for_update(self):
        sql, params = self.query.get_compiler(self.db).as_sql()
        return self.model._default_manager.raw(sql.rstrip() + ' FOR UPDATE', params)


class ForUpdateManager(Manager):
    def get_query_set(self):
        return ForUpdateQuerySet(self.model, using=self._db)
