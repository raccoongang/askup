"""Admin views"""

from django.contrib import admin

from .models import EmailPattern, Organization, Question, Qset


class OrganizationAdmin(admin.ModelAdmin):
    """Admin view for the Organization model"""
    list_display = ('name', 'email_patterns')
    fields = (
        'name',
        'for_any_authenticated',
        'for_unauthenticated',
        'show_authors',
        'own_questions_only',
        'users',
    )

    @staticmethod
    def email_patterns(obj):
        """Return email-patters of the organization comma separated"""
        return ", ".join(tuple(ep.text for ep in obj.emailpattern_set.all()))

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        return queryset.order_by('name')


class QsetAdmin(admin.ModelAdmin):
    """Admin list and detailed view for the Qset model"""
    fields = (
        'parent_qset',
        'name',
        'type',
        'for_any_authenticated',
        'for_unauthenticated',
        'show_authors',
        'own_questions_only',
    )
    list_display = ('name', 'parent_qset', 'type')

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        return queryset.filter(parent_qset_id__isnull=False).order_by('parent_qset_id', 'name')

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        form.base_fields['parent_qset'].required = True
        queryset = Qset.objects

        if obj and obj.id:
            queryset = queryset.exclude(id=obj.id)

        form.base_fields['parent_qset'].queryset = queryset.order_by('name', 'parent_qset_id')
        form.base_fields['type'].initial = 0
        return form


class QuestionAdmin(admin.ModelAdmin):
    """Admin list and detailed view for the Question model"""
    list_display = ('text', 'qset')

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        form.base_fields['qset'].queryset = Qset.objects.filter(
            parent_qset_id__isnull=False, type__in=(-1, 2)
        )
        return form

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        return queryset.order_by('text', 'qset')


class EmailPatternAdmin(admin.ModelAdmin):
    """Admin list and detailed view for the EmailPattern model"""
    list_display = ('text', 'organization')


admin.site.register(Organization, OrganizationAdmin)
admin.site.register(Qset, QsetAdmin)
admin.site.register(Question, QuestionAdmin)
admin.site.register(EmailPattern, EmailPatternAdmin)
