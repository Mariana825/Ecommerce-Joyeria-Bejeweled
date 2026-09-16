from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User

from .models import DireccionEnvio, Perfil


class RegistroForm(UserCreationForm):
    email = forms.EmailField(required=True, label='Correo electrónico')
    first_name = forms.CharField(required=True, label='Nombre')
    last_name = forms.CharField(required=False, label='Apellido')

    class Meta:
        model = User
        fields = ['username', 'first_name', 'last_name', 'email', 'password1', 'password2']

    def clean_email(self):
        email = self.cleaned_data['email']
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError('Ya existe una cuenta registrada con ese correo.')
        return email


class EdicionPerfilForm(forms.ModelForm):
    first_name = forms.CharField(required=True, label='Nombre')
    last_name = forms.CharField(required=False, label='Apellido')
    email = forms.EmailField(required=True, label='Correo electrónico')

    class Meta:
        model = Perfil
        fields = ['telefono', 'fecha_nacimiento', 'avatar']
        widgets = {
            'fecha_nacimiento': forms.DateInput(attrs={'type': 'date'}),
        }

    def __init__(self, *args, **kwargs):
        self.usuario = kwargs.pop('usuario', None)
        super().__init__(*args, **kwargs)
        if self.usuario:
            self.fields['first_name'].initial = self.usuario.first_name
            self.fields['last_name'].initial = self.usuario.last_name
            self.fields['email'].initial = self.usuario.email

    def save(self, commit=True):
        perfil = super().save(commit=False)
        if self.usuario:
            self.usuario.first_name = self.cleaned_data['first_name']
            self.usuario.last_name = self.cleaned_data['last_name']
            self.usuario.email = self.cleaned_data['email']
            if commit:
                self.usuario.save()
        if commit:
            perfil.save()
        return perfil


class DireccionEnvioForm(forms.ModelForm):
    class Meta:
        model = DireccionEnvio
        exclude = ['usuario', 'creado']
        widgets = {
            'etiqueta': forms.TextInput(attrs={'placeholder': "Ej: Casa, Oficina"}),
        }
