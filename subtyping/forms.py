from django.forms import ModelForm
from django.core.exceptions import FieldError
from django.contrib.contenttypes import forms as ct_forms

from subtyping.fields import BaseTypeForeignKey


def subtype_inlineformset_factory(
        parent_model, model, form=ModelForm,
        formset=ct_forms.BaseGenericInlineFormSet, fk_name=None, fields=None,
        exclude=None, extra=3, can_order=False, can_delete=True, max_num=None,
        formfield_callback=None, validate_max=False, for_concrete_model=True):
    """
    Returns a ``GenericInlineFormSet`` for the given kwargs.

    The ``ct_field`` and ``fk_field`` are determined by the
    ``BaseTypeForeignKey`` that provides the relationship between
    ``parent_model`` and model.

    If ``model`` has more than one ``BaseTypeForeignKey`` to ``parent_model``,
    you must provide ``fk_name``.
    """
    fk = get_basetype_foreign_key(parent_model, model, fk_name=fk_name)
    return ct_forms.generic_inlineformset_factory(
        model, form, formset=formset, ct_field=fk.ct_field,
        fk_field=fk.fk_field, fields=fields, exclude=exclude, extra=extra,
        can_order=can_order, can_delete=can_delete, max_num=max_num,
        formfield_callback=formfield_callback, validate_max=validate_max,
        for_concrete_model=for_concrete_model)


def get_basetype_foreign_key(parent_model, model, fk_name=None,
                             can_fail=False):
    """
    Finds and returns the BaseTypeForeignKey from model to parent if there is
    one (returns None if can_fail is True and no such field exists). If fk_name
    is provided, assume it is the name of the BaseTypeForeignKey field. Unles
    can_fail is True, an exception is raised if there is no BaseTypeForeignKey
    from model to parent_model.
    """
    opts = model._meta
    base_type = parent_model._subtyping._base_type
    if fk_name:
        try:
            fk = opts.get_field_by_name(fk_name)[0]
        except FieldError:
            msg = "'{0}.{1}' has no field named '{2}'."
            raise ValueError(msg.format(
                model._meta.app_label, model._meta.object_name, fk_name))

        if not (isinstance(fk, BaseTypeForeignKey)
                or fk.base_model != base_type):
            msg = "fk_name '{0}' is not a BaseTypeForeignKey to {1}.{2}'."
            raise ValueError(msg.format(
                fk_name, base_type._meta.app_label,
                base_type._meta.object_name))
    else:
        # Try to discover the BaseTypeForeignKey from model to parent_model
        fks_to_parent = []
        for f_name in opts.get_all_field_names():
            f = opts.get_field_by_name(f_name)[0]
            if isinstance(f, BaseTypeForeignKey) and f.base_model == base_type:
                fks_to_parent.append(f)
        if len(fks_to_parent) == 1:
            fk = fks_to_parent[0]
        elif len(fks_to_parent) == 0:
            if can_fail:
                return
            msg = "'{0}.{1}' has no BaseTypeForeignKey to '{2}.{3}'."
            raise ValueError(msg.format(
                model._meta.app_label, model._meta.object_name,
                parent_model._meta.app_label, parent_model._meta.object_name))
        else:
            msg = ("'{0}.{1}' has more than one BaseTypeForeignKey "
                   "to '{2}.{3}'.")
            raise ValueError(msg.format(
                model._meta.app_label, model._meta.object_name,
                parent_model._meta.app_label, parent_model._meta.object_name))
    return fk
