from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('download/', views.download_readme, name='download_readme'),
    path('render-markdown/', views.render_markdown, name='render_markdown'),
]
