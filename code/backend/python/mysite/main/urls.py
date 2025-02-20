from . import views
from django.urls import path

urlpatterns = [
    path('login', views.login_view, name='login'),
    path('logout', views.logout_view, name='logout'),
    path('signup', views.signup, name='signup'),
    path('instances', views.instances, name='instances'),
    path('', views.home, name='home')
]