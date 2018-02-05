"""Admin views."""
from django.contrib import admin
from django.contrib.auth.models import User

from .forms import UserForm
from .models import EmailPattern, Organization, Qset, Question


class OrganizationFilter(admin.SimpleListFilter):
    """Provides an organization filter for the Qsets and Questions lists."""

    title = 'Organization'
    parameter_name = 'org'
    template = 'askup/filters/dropdown_filter.html'

    def lookups(self, request, model_admin):
        """Return a set of filter elements."""
        items = [(org.id, org.name) for org in Organization.objects.all()]
        return items

    def queryset(self, request, queryset):
        """Return a queryset modified correspondingly to a filter."""
        if queryset.model is Question:
            return self.apply_question_queryset(queryset)
        elif queryset.model is Qset:
            return self.apply_qset_queryset(queryset)

        return queryset

    def apply_question_queryset(self, queryset):
        """Apply question queryset."""
        if self.value():
            return queryset.filter(qset__top_qset_id=self.value())

    def apply_qset_queryset(self, queryset):
        """Apply qset queryset."""
        if self.value():
            return queryset.filter(top_qset_id=self.value())


class OrganizationAdmin(admin.ModelAdmin):
    """Admin view for the Organization model."""

    list_display = ('name', 'email_patterns')
    fields = (
        'name',
        'users',
    )

    @staticmethod
    def email_patterns(obj):
        """Return email-patters of the organization comma separated."""
        return ", ".join(tuple(pattern.text for pattern in obj.emailpattern_set.all()))

    def get_queryset(self, request):
        """
        Get queryset for the list view.

        Overriding the queriset for the admin list view of the Organization
        """
        return super().get_queryset(request).order_by('name')


class QsetAdmin(admin.ModelAdmin):
    """Admin list and detailed view for the Qset model."""

    fields = (
        'parent_qset',
        'name',
        'for_any_authenticated',
        'for_unauthenticated',
        'show_authors',
        'own_questions_only',
    )
    list_display = ('name', 'parent_qset', 'type')
    list_filter = (OrganizationFilter,)

    class Media:
        js = ('assets/hide_add_edit_icons.js',)

    def get_queryset(self, request):
        """
        Get queryset for the list view.

        Override the queriset for the admin list view of the Qset.
        """
        return super().get_queryset(request).filter(parent_qset_id__isnull=False).order_by(
            'parent_qset_id',
            'name',
        )

    def get_form(self, request, obj=None, **kwargs):
        """
        Get queryset for the list view.

        Overriding the form fields for the admin model form of the Qset.
        """
        form = super().get_form(request, obj, **kwargs)
        form.base_fields['parent_qset'].label = 'Organization'
        form.base_fields['parent_qset'].required = True
        queryset = Qset.objects

        if obj and obj.id:
            queryset = queryset.filter(parent_qset_id=None).exclude(id=obj.id)

        form.base_fields['parent_qset'].queryset = queryset.order_by('name', 'parent_qset_id')
        return form


class QuestionAdmin(admin.ModelAdmin):
    """Admin list and detailed view for the Question model."""

    fields = (
        'text',
        'answer_text',
        'qset',
        'blooms_tag',
        'vote_value',
    )
    list_display = ('text', 'qset')
    list_filter = (OrganizationFilter,)

    def get_form(self, request, obj=None, **kwargs):
        """
        Get queryset for the list view.

        Overriding the form fields for the admin model form of the Questions.
        """
        form = super().get_form(request, obj, **kwargs)
        form.base_fields['qset'].queryset = Qset.objects.filter(
            parent_qset_id__isnull=False, type__in=(0, 2)
        )
        return form

    def get_queryset(self, request):
        """
        Get queryset for the list view.

        Override the queriset for the admin list view of the Questions.
        """
        queryset = super().get_queryset(request)
        return queryset.order_by('text', 'qset')

    def get_readonly_fields(self, request, obj=None):
        """Return a tuple of field names that should behave as a read only."""
        return ('vote_value',)


class EmailPatternAdmin(admin.ModelAdmin):
    """Admin list and detailed view for the EmailPattern model."""

    fields = ('organization', 'text')
    list_display = ('organization', 'text')


class UserAdmin(admin.ModelAdmin):
    """Admin list and detailed view for the Qset model."""

    form = UserForm
    list_display = ('username', 'email', 'first_name', 'last_name')


admin.site.register(Organization, OrganizationAdmin)
admin.site.register(Qset, QsetAdmin)
admin.site.register(Question, QuestionAdmin)
admin.site.register(EmailPattern, EmailPatternAdmin)
admin.site.unregister(User)
admin.site.register(User, UserAdmin)
