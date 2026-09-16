from django import forms

from .models import Resena, Suscriptor


class ResenaForm(forms.ModelForm):
    CALIFICACIONES = [
        (5, '★★★★★ — Excelente'),
        (4, '★★★★☆ — Muy buena'),
        (3, '★★★☆☆ — Buena'),
        (2, '★★☆☆☆ — Regular'),
        (1, '★☆☆☆☆ — Mala'),
    ]

    calificacion = forms.TypedChoiceField(
        choices=CALIFICACIONES, coerce=int, label='Tu calificación'
    )

    class Meta:
        model = Resena
        fields = ['calificacion', 'comentario']
        labels = {'comentario': 'Tu reseña'}
        widgets = {
            'comentario': forms.Textarea(attrs={
                'placeholder': 'Cuéntanos qué te pareció la pieza: calidad, terminado, si es como en las fotos...',
                'rows': 4,
            }),
        }


class SuscriptorForm(forms.ModelForm):
    class Meta:
        model = Suscriptor
        fields = ['email']
        widgets = {
            'email': forms.EmailInput(attrs={'placeholder': 'Tu correo electrónico'}),
        }
