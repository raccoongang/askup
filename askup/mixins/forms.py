import re

from crispy_forms.layout import ButtonHolder, HTML, Submit
from django import forms
from django.contrib.auth.models import User
from django.urls import reverse


class InitFormWithCancelButtonMixIn(object):
    """Provides the methods to implement into some ModelForm successors."""

    def __init__(self, *args, **kwargs):
        """
        Init the ModelForm with the _setup_fiels and _setup_helper invocation.

        Overriding the same method of the forms.ModelForm.

        User object is provided as a keyword argument to be passed into the
        _set_up_fields to filter a user-related data.

        Qset id is provided as a keyword argument to be passed into the
        "cancel" button generator method.
        """
        user = kwargs.pop('user', None)
        qset_id = kwargs.pop('qset_id', None)
        super().__init__(*args, **kwargs)
        self._set_up_fields(user or getattr(self, 'current_user', None))
        self._set_up_helper(qset_id)

    def _set_up_fields(self, user):
        """Set up the form fields."""
        pass

    def _set_up_helper(self, qset_id):
        """Set up the form helper (layout)."""
        pass

    def _get_helper_buttons(self, qset_id, submit_name='Save'):
        """Return helper buttons that will bet presented in the html form later."""
        return ButtonHolder(
            self._get_cancel_button(qset_id),
            Submit('submit', submit_name, css_class='btn btn-theme'),
            css_class='center',
        )

    def _get_cancel_button(self, qset_id):
        """Return cancel button element of the form layout."""
        if qset_id:
            cancel_url = reverse('askup:qset', kwargs={'pk': qset_id})
        else:
            cancel_url = reverse('askup:organizations')

        return HTML(
            '<a class="btn btn-flat cancel-btn" href="{0}">'.format(cancel_url) +
            'Cancel' +
            '</a>'
        )


class UsernameCleanMixIn(object):
    """
    Provides the method that makes an additional validates on username field of User model.
    """

    _username_pattern = re.compile(r'^[\w-]+$')

    def clean_username(self):
        """
        Validate the username field.
        """
        if not self._username_pattern.match(self.cleaned_data['username']):
            raise forms.ValidationError(
                'Can contain only latin characters, digits, - or _'
            )

        username_queryset = User.objects.filter(username__iexact=self.cleaned_data['username'])

        if self.instance.id:
            username_queryset = username_queryset.exclude(id=self.instance.id)

        if username_queryset.exists():
            raise forms.ValidationError("This username is already used")

        return self.cleaned_data['username']
