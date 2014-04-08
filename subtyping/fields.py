from django.contrib.contenttypes.fields import (GenericForeignKey,
                                                GenericRelation)
from django.contrib.contenttypes.models import ContentType
from django.db import models


class BaseTypeForeignKey(GenericForeignKey):
    """
    This field subclasses GenericForeignKey, while automatically adding the
    content_type and object_id fields. It also adds a "reverse" relationship
    for each subtype of the given base model model in the form of a
    GenericRelation field on those models.
    """
    def __init__(self, base_model, related_name=None, ct_field=None,
                 fk_field=None, blank=False, null=False):
        ct_field = ct_field or base_model._subtyping.default_ct_field
        fk_field = fk_field or base_model._subtyping.default_fk_field
        self.base_model = base_model
        self.ct_field = ct_field
        self.fk_field = fk_field
        self.related_name = related_name
        self.blank = blank
        self.null = null
        super(BaseTypeForeignKey, self).__init__(ct_field, fk_field)

    def get_type_choices(self):
        return {'pk__in': self.base_model.get_subtypes()}

    def contribute_to_class(self, model, name):
        super(BaseTypeForeignKey, self).contribute_to_class(model, name)

        # Add contenttype and fk fields, but only on concrete models.
        if model._meta.abstract:
            return

        field_kwargs = {
            'blank': self.blank,
            'null': self.null,
            'editable': False
        }
        ct_related_name = self.ct_field + '_' + model._meta.model_name

        ct = models.ForeignKey(ContentType,
                               limit_choices_to=self.get_type_choices,
                               related_name=ct_related_name,
                               **field_kwargs)
        fk = models.PositiveIntegerField(**field_kwargs)

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
