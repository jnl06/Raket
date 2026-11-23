
from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import UserCreationForm

from .models import Profile

User = get_user_model()


class SignupForm(UserCreationForm):

    full_name = forms.CharField(
        max_length=150,
        widget=forms.TextInput(attrs={
            'placeholder': 'Enter your full name',
            'class': 'form-input'
        })
    )

    email = forms.EmailField(
        widget=forms.EmailInput(attrs={
            'placeholder': 'Enter your email address',
            'class': 'form-input'
        })
    )

    phone = forms.CharField(
        max_length=20,
        widget=forms.TextInput(attrs={
            'placeholder': 'Enter your phone number',
            'class': 'form-input'
        })
    )

    role = forms.ChoiceField(
        choices=Profile.Role.choices,
        initial=Profile.Role.SEEKER,
        widget=forms.HiddenInput()
    )

    password1 = forms.CharField(
        label='Password',
        widget=forms.PasswordInput(attrs={
            'placeholder': 'Create a password',
            'class': 'form-input'
        })
    )

    password2 = forms.CharField(
        label='Confirm Password',
        widget=forms.PasswordInput(attrs={
            'placeholder': 'Confirm your password',
            'class': 'form-input'
        })
    )

    class Meta:
        model = User
        fields = ('username', 'email', 'password1', 'password2')

    def clean_email(self):
        email = self.cleaned_data['email']

        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError(
                'This email is already registered.'
            )

        return email

    def save(self, commit=True):
        user = super().save(commit=False)

        user.email = self.cleaned_data['email']

        full_name = self.cleaned_data['full_name'].strip()
        name_parts = full_name.split(maxsplit=1)

        user.first_name = name_parts[0]
        user.last_name = name_parts[1] if len(name_parts) > 1 else ''

        if commit:
            user.save()

            Profile.objects.create(
                user=user,
                full_name=full_name,
                phone=self.cleaned_data['phone'],
                role=self.cleaned_data['role']
            )

        return user
