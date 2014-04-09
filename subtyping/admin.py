from django.contrib.contenttypes.admin import GenericInlineModelAdmin

from subtyping.forms import get_basetype_foreign_key


class SubTypeInline(GenericInlineModelAdmin):
    fk_name = None

    def get_formset(self, request, obj=None, **kwargs):
        fk = get_basetype_foreign_key(self.parent_model, self.model,
                                      fk_name=self.fk_name)
        defaults = {
            'ct_field': fk.ct_field,
            'fk_field': fk.fk_field
        }
        defaults.update(kwargs)
        return super(SubTypeInline, self).get_formset(request, obj, **defaults)
