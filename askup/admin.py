import logging
from django.contrib import admin
from .models import Qset, Question, Organization, EmailPattern

from django.forms.fields import TypedChoiceField


logging.root.setLevel(logging.DEBUG)


class OrganizationAdmin(admin.ModelAdmin):
    list_display = ('name', 'email_patterns')
    exclude = ('parent_qset', 'type', 'questions_count')

    def email_patterns(self, obj):
        return ", ".join(tuple(ep.text for ep in obj.emailpattern_set.all()))

    def get_queryset(self, request):
        queryset = super(OrganizationAdmin, self).get_queryset(request)
        return queryset.order_by('name')


class QsetAdmin(admin.ModelAdmin):
    exclude = ('questions_count', )
    list_display = ('name', 'parent_qset', 'type')

    def get_queryset(self, request):
        queryset = super(QsetAdmin, self).get_queryset(request)
        return queryset.filter(parent_qset_id__isnull=False).order_by('parent_qset_id', 'name')

    def get_form(self, request, obj=None, **kwargs):
        form = super(QsetAdmin, self).get_form(request, obj, **kwargs)
        form.base_fields['parent_qset'].required = True
        queryset = Qset.objects

        if obj and obj.id:
            queryset = queryset.exclude(id=obj.id)

        form.base_fields['parent_qset'].queryset = queryset.order_by('name', 'parent_qset_id')
        logging.debug('FIELD: {0}'.format(form.base_fields['type']))
        form.base_fields['type'].initial = 0

        return form


class QuestionAdmin(admin.ModelAdmin):
    list_display = ('text', 'qset')

    def get_form(self, request, obj=None, **kwargs):
        form = super(QuestionAdmin, self).get_form(request, obj, **kwargs)
        form.base_fields['qset'].queryset = Qset.objects.filter(parent_qset_id__isnull=False, type__in=(0, 2))
        return form

    def get_queryset(self, request):
        queryset = super(QuestionAdmin, self).get_queryset(request)
        return queryset.order_by('text', 'qset')


class EmailPatternAdmin(admin.ModelAdmin):
    list_display = ('text', 'organization')


admin.site.register(Organization, OrganizationAdmin)
admin.site.register(Qset, QsetAdmin)
admin.site.register(Question, QuestionAdmin)
admin.site.register(EmailPattern, EmailPatternAdmin)
