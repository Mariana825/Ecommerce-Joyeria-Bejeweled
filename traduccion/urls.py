from django.urls import path

from . import views

app_name = 'traduccion'

urlpatterns = [
    path('cambiar/', views.cambiar_idioma, name='cambiar_idioma'),
]
