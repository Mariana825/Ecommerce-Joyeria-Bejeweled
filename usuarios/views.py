from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render

from .forms import DireccionEnvioForm, EdicionPerfilForm, RegistroForm
from .models import DireccionEnvio


def registro(request):
    if request.user.is_authenticated:
        return redirect('productos:catalogo')

    if request.method == 'POST':
        form = RegistroForm(request.POST)
        if form.is_valid():
            usuario = form.save()
            login(request, usuario)
            messages.success(request, f'¡Bienvenido/a, {usuario.first_name or usuario.username}! Tu cuenta fue creada correctamente.')
            return redirect('productos:catalogo')
    else:
        form = RegistroForm()

    return render(request, 'usuarios/registro.html', {'form': form})


@login_required
def perfil(request):
    perfil_usuario = request.user.perfil

    if request.method == 'POST':
        form = EdicionPerfilForm(request.POST, request.FILES, instance=perfil_usuario, usuario=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Tu perfil se actualizó correctamente.')
            return redirect('usuarios:perfil')
    else:
        form = EdicionPerfilForm(instance=perfil_usuario, usuario=request.user)

    return render(request, 'usuarios/perfil.html', {'form': form})


@login_required
def lista_direcciones(request):
    direcciones = request.user.direcciones.all()
    return render(request, 'usuarios/direcciones.html', {'direcciones': direcciones})


@login_required
def crear_direccion(request):
    if request.method == 'POST':
        form = DireccionEnvioForm(request.POST)
        if form.is_valid():
            direccion = form.save(commit=False)
            direccion.usuario = request.user
            direccion.save()
            messages.success(request, 'Dirección agregada correctamente.')
            return redirect('usuarios:direcciones')
    else:
        form = DireccionEnvioForm()

    return render(request, 'usuarios/direccion_form.html', {'form': form, 'titulo': 'Nueva dirección'})


@login_required
def editar_direccion(request, pk):
    direccion = get_object_or_404(DireccionEnvio, pk=pk, usuario=request.user)

    if request.method == 'POST':
        form = DireccionEnvioForm(request.POST, instance=direccion)
        if form.is_valid():
            form.save()
            messages.success(request, 'Dirección actualizada correctamente.')
            return redirect('usuarios:direcciones')
    else:
        form = DireccionEnvioForm(instance=direccion)

    return render(request, 'usuarios/direccion_form.html', {'form': form, 'titulo': 'Editar dirección'})


@login_required
def eliminar_direccion(request, pk):
    direccion = get_object_or_404(DireccionEnvio, pk=pk, usuario=request.user)
    if request.method == 'POST':
        direccion.delete()
        messages.success(request, 'Dirección eliminada.')
        return redirect('usuarios:direcciones')
    return render(request, 'usuarios/direccion_confirmar_eliminar.html', {'direccion': direccion})


@login_required
def historial_pedidos(request):
    # Import local para evitar dependencia circular entre apps.
    from pedidos.models import Pedido
    pedidos = Pedido.objects.filter(usuario=request.user).order_by('-creado')
    return render(request, 'usuarios/historial_pedidos.html', {'pedidos': pedidos})
