"""
URL configuration for q4s_site_monitoring project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import include, path, re_path
from rest_framework import routers
from core.views import (
    OPCGeneratedSiteLinkViewSet,
    SiteDashboardAccessView,
)
from django.shortcuts import render

def index(request, path=''):
    if path:
        import os
        from django.conf import settings
        from django.views.static import serve
        full_path = os.path.join(settings.FRONTEND_DIR, path)
        if os.path.exists(full_path) and os.path.isfile(full_path):
            return serve(request, path, document_root=settings.FRONTEND_DIR)
    return render(request, 'index.html')

router = routers.DefaultRouter()
router.register(r'opc-generated-site-links', OPCGeneratedSiteLinkViewSet)

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include(router.urls)),
    path('api/site-dashboard/<str:link_id>/access/',
         SiteDashboardAccessView.as_view(),
         name='site-dashboard-access'),
    
    # Flutter Web Catch-all (SPA Routing + Static Files)
    re_path(r'^(?P<path>.*)$', index, name='index'),
]
