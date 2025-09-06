from django.urls import path
from . import views

app_name = 'main_app'

urlpatterns = [
    path('', views.index, name='index'),
    path('employees/', views.employees_table, name='employees_table'),
    path('generate-test-calls/', views.generate_test_calls, name='generate_test_calls'),
]
