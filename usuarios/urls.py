from django.conf import settings
from django.contrib.auth import views as auth_views
from django.urls import path

from . import views

app_name = 'usuarios'

urlpatterns = [
    # Autenticación
    path('registro/', views.registro, name='registro'),
    path('login/', auth_views.LoginView.as_view(template_name='usuarios/login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),

    # Recuperación de contraseña (flujo estándar de Django)
    path('contrasena/recuperar/', auth_views.PasswordResetView.as_view(
        template_name='usuarios/contrasena_recuperar.html',
        email_template_name='usuarios/contrasena_email.html',
        subject_template_name='usuarios/contrasena_asunto.txt',
        success_url='/cuenta/contrasena/recuperar/enviado/',
        extra_email_context={'site_url': settings.SITE_URL},
    ), name='password_reset'),
    path('contrasena/recuperar/enviado/', auth_views.PasswordResetDoneView.as_view(
        template_name='usuarios/contrasena_recuperar_enviado.html',
    ), name='password_reset_done'),

    # "hecho/" va ANTES de la ruta con <uidb64>/<token>/
    path('contrasena/reset/hecho/', auth_views.PasswordResetCompleteView.as_view(
        template_name='usuarios/contrasena_completa.html',
    ), name='password_reset_complete'),
    path('contrasena/reset/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(
        template_name='usuarios/contrasena_confirmar.html',
        success_url='/cuenta/contrasena/reset/hecho/',
    ), name='password_reset_confirm'),

    # Perfil y cuenta
    path('perfil/', views.perfil, name='perfil'),
    path('direcciones/', views.lista_direcciones, name='direcciones'),
    path('direcciones/nueva/', views.crear_direccion, name='direccion_nueva'),
    path('direcciones/<int:pk>/editar/', views.editar_direccion, name='direccion_editar'),
    path('direcciones/<int:pk>/eliminar/', views.eliminar_direccion, name='direccion_eliminar'),
    path('pedidos/', views.historial_pedidos, name='historial_pedidos'),
]