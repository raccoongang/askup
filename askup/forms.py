import logging

from django import forms
from django.contrib.auth import authenticate
from django.db.models.expressions import RawSQL

from .models import Organization, Qset


log = logging.getLogger(__name__)


class UserLoginForm(forms.Form):
    """Handles the user login form behaviour."""

    username = forms.CharField()
    password = forms.CharField(widget=forms.PasswordInput)

    def clean(self, *args, **kwargs):
        """
        Validate the login form fields.

        Overriding the same method of the forms.Form
        """
        username = self.cleaned_data.get('username')
        password = self.cleaned_data.get('password')
        user = authenticate(username=username, password=password)

        if not user:
            raise forms.ValidationError("This user doesn't exist")

        if not user.check_password(password):
            raise forms.ValidationError("Incorrect password")

        if not user.is_active:
            raise forms.ValidationError("This user is no longer active")

        return super().clean(*args, **kwargs)


class OrganizationModelForm(forms.ModelForm):
    """Provides the create/update functionality for the Organization."""

    class Meta:
        model = Organization
        fields = (
            'name',
        )


class QsetModelForm(forms.ModelForm):
    """Provides the create/update functionality for the Qset."""

    def __init__(self, *args, **kwargs):
        """
        Init the QsetModelForm.

        Overriding the same method of the forms.ModelForm
        """
        user = kwargs.pop('user')  # User object is always present
        super().__init__(*args, **kwargs)

        self.fields['parent_qset'].required = True
        self.fields['parent_qset'].empty_label = None

        if user.id:
            if user.is_superuser:
                queryset = Qset.objects.all()
            else:
                queryset = Qset.objects.filter(top_qset__users=user.id)

            queryset = queryset.annotate(
                customized_name=RawSQL(
                    'case when askup_qset.parent_qset_id is null' +
                    " then askup_qset.name else concat('— ', askup_qset.name) end",
                    tuple()
                ),
                is_organization=RawSQL('askup_qset.parent_qset_id is null', tuple()),
            )
            queryset = queryset.order_by('top_qset_id', '-is_organization', 'askup_qset.name')
            self.fields['parent_qset'].queryset = queryset

    class Meta:
        model = Qset
        fields = (
            'name',
            'parent_qset',
            'type',
            'for_any_authenticated',
            'show_authors',
            'for_unauthenticated',
        )


class QsetDeleteModelForm(forms.ModelForm):
    """Provides the delete functionality for the Qset."""

    class Meta:
        model = Qset
        fields = []
