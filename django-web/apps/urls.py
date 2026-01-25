"""
URL configuration for apps application.
"""
from django.urls import path
from django.contrib.auth.views import LoginView, LogoutView
from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('login/', LoginView.as_view(template_name='apps/login.html'), name='login'),
    path('logout/', LogoutView.as_view(), name='logout'),
]
