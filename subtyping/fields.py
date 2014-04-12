from django.core import exceptions
from django.db import models
from django.db.models.sql.datastructures import Col
from django.utils import six
from django.contrib.contenttypes.fields import (GenericForeignKey,
                                                GenericRelation)
from django.contrib.contenttypes.models import ContentType


class BaseTypeForeignKey(GenericForeignKey):
    """
    This field subclasses GenericForeignKey, while automatically adding the
    content_type and object_id fields. It also adds a "reverse" relationship
    for each subtype of the given base model model in the form of a
    GenericRelation field on those models.
    """
    def __init__(self, base_model, related_name=None, ct_field=None,
                 fk_field=None, blank=False, null=False, db_index=True):
        self.base_model = base_model
        self.ct_field = ct_field
        self.fk_field = fk_field
        self.related_name = related_name
        self.blank = blank
        self.null = null
        self.db_index = db_index
        super(BaseTypeForeignKey, self).__init__(ct_field, fk_field)

    def get_type_choices(self):
        return {'pk__in': self.base_model.get_subtypes()}

    def contribute_to_class(self, model, name):
        super(BaseTypeForeignKey, self).contribute_to_class(model, name)

        if not self.ct_field:
            self.ct_field = '{}_type'.format(name)

        if not self.fk_field:
            self.fk_field = '{}_id'.format(name)

        # Add contenttype and fk fields, but only on concrete models.
        if model._meta.abstract:
            return

        # add the fields once the base model is prepared so that we can acccess
        # base_mode._meta.pk (needed to create the fk_field).
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

        # Add generic relation to subtypes
        for type in self.base_model._subtyping.subtypes:
            rel = GenericRelation(
                model,
                content_type_field=self.ct_field,
                object_id_field=self.fk_field,
                related_query_name=type._meta.model_name
            )
            type.add_to_class(self.related_name, rel)

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

    def get_lookup_constraint(self, constraint_class, alias, targets, sources,
                              lookups, raw_value):

        from django.db.models.sql.where import AND
        root_constraint = constraint_class()
        assert len(targets) == len(sources)
        if len(lookups) > 1:
            raise exceptions.FieldError(
                'Relation fields do not support nested lookups')
        lookup_type = lookups[0]

        source = target = sources[0].model._meta.get_field_by_name(
            self.fk_field)[0]

        if lookup_type == 'isnull':
            return source.get_lookup_constraint(constraint_class, alias,
                                                targets, sources)

        elif lookup_type == 'exact':
            if not isinstance(raw_value, self.base_model):
                raise ValueError("{0!r} is not an instance of {1!r}".format(
                                 raw_value, self.base_model))

            ct = ContentType.objects.get_for_model(raw_value)

            ct_source = ct_target = source.model._meta.get_field_by_name(
                self.ct_field)[0]
            ct_lookup_class = ct_source.get_lookup(lookup_type)
            root_constraint.add(ct_lookup_class(
                Col(alias, ct_target, ct_source), ct.pk), AND)

            target_lookup_class = target.get_lookup(lookup_type)
            root_constraint.add(target_lookup_class(
                Col(alias, target, source), raw_value.pk), AND)

        else:
            raise TypeError('Invalid lookup {0} for BaseTypeForeignKey'
                            .format(lookup_type))
        return root_constraint
