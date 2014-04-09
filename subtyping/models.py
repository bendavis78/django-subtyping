from django.db import models
from django.db.models.base import ModelBase
from django.contrib.contenttypes.models import ContentType


class BaseType(ModelBase):
    def __new__(cls, name, bases, attrs):
        super_new = super(BaseType, cls).__new__
        if name == 'NewBase' and attrs == {}:
            return super_new(cls, name, bases, attrs)
        new_class = super_new(cls, name, bases, attrs)

        subtyping = attrs.pop('Subtyping', None)
        opts = SubtypingOptions(subtyping)

        if not new_class._meta.abstract:
            # This is a concrete subtype
            base_types = [b for b in bases if isinstance(b, BaseType)
                          and b._meta.abstract]

            if len(base_types) > 1:
                raise TypeError("BaseTypeModel subclasses may not inherit "
                                "from more than one BaseTypeModel abstract "
                                "class")

            opts._base_type = base_types[0]
            opts._base_type._subtyping._ancestors.append(new_class)

        new_class.add_to_class('_subtyping', opts)
        return new_class


class SubtypingOptions(object):
    def __init__(self, meta):
        self.meta = meta
        self._ancestors = []
        self._subtypes = []
        self._base_type = None
        self.default_ct_field = None
        self.default_fk_field = None

    def contribute_to_class(self, cls, name):
        cls._subtyping = self
        self.model = cls
        self.default_ct_field = '{}_type'.format(self.model._meta.model_name)
        self.default_fk_field = '{}_id'.format(self.model._meta.model_name)

        # apply overrides from meta
        if self.meta:
            self._subtypes = getattr(self.meta, 'subtypes', self.subtypes)
            self.default_ct_field = getattr(self.meta, 'default_ct_field',
                                            self.default_ct_field)
            self.default_fk_field = getattr(self.meta, 'default_fk_field',
                                            self.default_fk_field)

    @property
    def subtypes(self):
        if self._subtypes:
            return self._subtypes
        return self._ancestors


class BaseTypeModel(models.Model):
    __metaclass__ = BaseType

    @classmethod
    def get_subtypes(cls):
        subtypes = cls._subtyping.subtypes
        names = (m._meta.model_name.lower() for m in subtypes)
        return ContentType.objects.filter(app_label=cls._meta.app_label,
                                          model__in=names)

    class Meta:
        abstract = True
