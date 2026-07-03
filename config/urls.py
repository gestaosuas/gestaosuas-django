from django.contrib import admin
from django.urls import include, path, register_converter
from apps.core.converters import DirectorateSlugConverter
from django.conf import settings
from django.conf.urls.static import static

register_converter(DirectorateSlugConverter, 'dir_slug')


urlpatterns = [
    path("admin/", admin.site.urls),
    path("", include("apps.core.urls")),
    path("accounts/", include("apps.accounts.urls")),
    path("directorias/", include("apps.directorates.urls")),
    path("monitoramento/", include("apps.monitoramento.urls")),
    path("cras/", include("apps.cras.urls")),
    path("beneficios/", include("apps.beneficios.urls")),
    path("sine-cp/", include("apps.sinecp.urls")),
    path("naica/", include("apps.naica.urls")),
    path("ceai/", include("apps.ceai.urls")),
    path("creasidoso/", include("apps.creasidoso.urls")),
    path("poprua/", include("apps.poprua.urls")),
    path("protecao-especial/", include("apps.protecaoespecial.urls")),
    path("casa-mulher/", include("apps.casamulher.urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

