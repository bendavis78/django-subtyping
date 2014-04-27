import operator

from django.db.models.lookups import Lookup, Transform, IsNull, Exact
from django.db.models.sql.datastructures import Col
from django.db.models.sql.query import LOOKUP_SEP
from django.db.models import Q


class BaseTypeForeignKeyExact(Exact):
    lookup_name = 'exact'

    def __init__(self, lhs, rhs):
        field = lhs.source
        self.fk_field = field.model._meta.get_field_by_name(field.fk_field)[0]
        lhs = Col(lhs.alias, self.fk_field, self.fk_field)
        super(BaseTypeForeignKeyExact, self).__init__(lhs, rhs)

    def get_prep_lookup(self):
        value = self.rhs._get_pk_val()
        return self.fk_field.get_prep_lookup(self.lookup_name, value)


class BaseTypeForeignKeyIsNull(IsNull):
    lookup_name = 'isnull'

    def __init__(self, lhs, rhs):
        field = lhs.source
        self.fk_field = field.model._meta.get_field_by_name(field.fk_field)[0]
        lhs = Col(lhs.alias, self.fk_field, self.fk_field)
        super(BaseTypeForeignKeyIsNull, self).__init__(lhs, rhs)


class SubTypeFieldLookup(Lookup):
    def __init__(self, lhs, rhs):
        # This doesn't currently work, because FROM clause is compiled before
        # we can get to it. This is here in case a workaround is found.
        raise NotImplementedError
        self.lhs, self.rhs = lhs, rhs
        self.field = lhs.lhs.source
        self.base_model = self.field.base_model

    def as_sql(self, qn, connection):
        filters = []
        for lookup in self.field._subtype_rel_map:
            lookup = LOOKUP_SEP.join([lookup] + self.lhs.init_lookups)
            filters.append(Q(**{lookup: self.rhs}))
        query_expr = reduce(operator.or_, filters)
        import ipdb; ipdb.set_trace()
        qn.query.add_q(query_expr)

        return '', []


class BaseTypeRelatedFieldTransform(Transform):
    def __init__(self, lhs, lookups):
        raise NotImplementedError
        self.lhs = lhs
        self.init_lookups = lookups[:]
        self.base_model = lhs.source.base_model
        self.rel_field = self.base_model._meta.get_field_by_name(
            lookups[0])[0]

    def get_lookup(self, lookup_name):
        return SubTypeFieldLookup

    @property
    def output_type(self):
        return self.rel_field
