from django.apps import apps
from django.db import models
from django.db.models.constants import LOOKUP_SEP
from django.utils import six
from django.contrib.contenttypes.fields import (GenericForeignKey,
                                                GenericRelation)
from django.contrib.contenttypes.models import ContentType

from subtyping import lookups
from subtyping.models import subtyping_class_prepared


class BaseTypeForeignKey(GenericForeignKey):
    """
    This field subclasses GenericForeignKey, while automatically adding the
    content_type and object_id fields. It also adds a "reverse" relationship
    for each subtype of the given base model model in the form of a
    GenericRelation field on those models.
    """

    def __init__(self, base_model, related_name=None, ct_field=None,
                 query_prefix=None, fk_field=None, blank=False, null=False,
                 limit_types_to=None, db_index=True):
        self.base_model = base_model
        self.ct_field = ct_field
        self.fk_field = fk_field
        self.related_name = related_name
        self.query_prefix = None
        self.blank = blank
        self.null = null
        self.db_index = db_index
        self.limit_types_to = limit_types_to
        self._subtype_rel_map = {}
        super(BaseTypeForeignKey, self).__init__(ct_field, fk_field)

    def get_type_choices(self):
        subtypes = []
        if self.limit_types_to:
            for model in self.limit_types_to:
                if isinstance(model, six.string_types):
                    model = apps.get_model(model)
                ct = ContentType.objects.get_for_model(model)
                subtypes.append(ct)
        else:
            subtypes = self.base_model.get_subtypes()

        return {'pk__in': (t.pk for t in subtypes)}

    def contribute_to_class(self, model, name):
        super(BaseTypeForeignKey, self).contribute_to_class(model, name)

        if not self.ct_field:
            self.ct_field = '{}_type'.format(name)

        if not self.fk_field:
            self.fk_field = '{}_id'.format(name)

        # Add contenttype and fk fields, but only on concrete models.
        if model._meta.abstract:
            return

        field_kwargs = {
            'blank': self.blank,
            'null': self.null,
            'db_index': self.db_index,
            'editable': False
        }
        ct_related_name = self.ct_field + '_' + model._meta.model_name

        ct = models.ForeignKey(ContentType,
                               limit_choices_to=self.get_type_choices,
                               related_name=ct_related_name,
                               **field_kwargs)
        base_pk = self._get_base_pk_field()
        if isinstance(base_pk, models.AutoField):
            fk = models.PositiveIntegerField(**field_kwargs)
        else:
            # clone the field using deconstruct()
            name, pth, args, kwargs = base_pk.deconstruct()
            kwargs['primary_key'] = False
            kwargs.update(field_kwargs)
            fk = base_pk.__class__(*args, **kwargs)

        model.add_to_class(self.ct_field, ct)
        model.add_to_class(self.fk_field, fk)

        if not self.related_name:
            self.related_name = self.model._meta.model_name + '_set'

        self.in_loop = False

        # Add the generic relation for this field to each subtype. We add a
        # signal handler for subtypes that have not been prepared yet.
        def add_generic_relation(sender, **kwargs):
            opts = sender._meta

            if not issubclass(sender, self.base_model) or opts.abstract:
                return

            prefix = self.query_prefix or (name + '_')
            query_name = opts.model_name
            if hasattr(sender, '_subtyping'):
                query_name = sender._subtyping.get_query_name()
            query_name = prefix + query_name

            rel = GenericRelation(
                model,
                content_type_field=self.ct_field,
                object_id_field=self.fk_field,
                related_query_name=query_name
            )
            self._subtype_rel_map[query_name] = rel
            sender.add_to_class(self.related_name, rel)

        self.in_loop = True
        for subtype in self.base_model._subtyping.subtypes:
            add_generic_relation(subtype)
        self.in_loop = False

        subtyping_class_prepared.connect(add_generic_relation, weak=False)

    def _get_base_pk_field(self):
        if not hasattr(self, '_base_pk_field'):
            opts = self.base_model._meta
            if opts.pk is not None:
                return opts.pk

            # use same pk-finding logic as django.db.models.Options._prepare
            if opts.parents:
                field = next(six.itervalues(opts.parents))
                already_created = [fld for fld in opts.local_fields
                                   if fld.name == field.name]
                if already_created:
                    field = already_created[0]
            else:
                field = models.AutoField(verbose_name='ID', primary_key=True,
                                         auto_created=True)
            self._base_pk_field = field

        return self._base_pk_field

    def get_lookup(self, lookup):
        parts = lookup.split(LOOKUP_SEP)
        if len(parts) == 1:
            if parts[0] == 'exact':
                return lookups.BaseTypeForeignKeyExact
            if parts[0] == 'isnull':
                return lookups.BaseTypeForeignKeyIsNull

    def get_transform(self, lookup):
        #return lookups.BaseTypeRelatedFieldTransform
        return None

    @property
    def column(self):
        return None
