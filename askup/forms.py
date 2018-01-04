from django import forms
from django.contrib.auth import authenticate


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
