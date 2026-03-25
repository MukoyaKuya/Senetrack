"""
URL configuration for root project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
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
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

from pathlib import Path

from django.http import HttpResponse, Http404, FileResponse
from django.shortcuts import render
from django.utils import timezone

def robots_txt(request):
    base = f"{request.scheme}://{request.get_host()}"
    lines = [
        "User-agent: *",
        f"Disallow: /{settings.DJANGO_ADMIN_PATH}/",
        "Disallow: /insights/export/csv/",
        "",
        f"Sitemap: {base}/sitemap.xml",
    ]
    return HttpResponse("\n".join(lines), content_type="text/plain")


def sitemap_xml(request):
    from scorecard.models import Senator, County
    base = f"{request.scheme}://{request.get_host()}"
    today = timezone.now().date().isoformat()
    static_urls = [
        ("", "1.0", "weekly"),
        ("senators/", "0.9", "weekly"),
        ("findings/", "0.8", "weekly"),
        ("bills/", "0.8", "weekly"),
        ("bills/analytics/", "0.7", "monthly"),
        ("insights/", "0.7", "weekly"),
        ("frontier/", "0.7", "weekly"),
        ("counties/", "0.7", "monthly"),
        ("compare/", "0.5", "monthly"),
        ("about/", "0.6", "monthly"),
    ]
    urls = []
    for path, priority, freq in static_urls:
        urls.append(
            f"  <url><loc>{base}/{path}</loc><lastmod>{today}</lastmod>"
            f"<changefreq>{freq}</changefreq><priority>{priority}</priority></url>"
        )
    for s in Senator.objects.filter(is_deceased=False).only("senator_id"):
        urls.append(
            f"  <url><loc>{base}/senator/{s.senator_id}/</loc>"
            f"<lastmod>{today}</lastmod><changefreq>weekly</changefreq><priority>0.8</priority></url>"
        )
    for c in County.objects.all().only("slug"):
        urls.append(
            f"  <url><loc>{base}/county/{c.slug}/</loc>"
            f"<lastmod>{today}</lastmod><changefreq>monthly</changefreq><priority>0.6</priority></url>"
        )
    xml = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        + "\n".join(urls)
        + "\n</urlset>"
    )
    return HttpResponse(xml, content_type="application/xml")


def admin_alias_page(request):
    return render(
        request,
        "scorecard/admin_alias.html",
        {
            "admin_url": f"/{settings.DJANGO_ADMIN_PATH}/",
            "image_url": "/admin/image/",
        },
    )


def admin_alias_image(request):
    image_path = settings.BASE_DIR / "scorecard" / "static" / "scorecard" / "images" / "admin_alias.png"
    if not image_path.exists():
        raise Http404("Admin alias image not found")
    return FileResponse(image_path.open("rb"), content_type="image/png")

urlpatterns = [
    path(f'{settings.DJANGO_ADMIN_PATH}/', admin.site.urls),
    path('admin', admin_alias_page, name='admin-alias'),
    path('admin/', admin_alias_page, name='admin-alias-slash'),
    path('admin/image/', admin_alias_image, name='admin-alias-image'),
    path('robots.txt', robots_txt),
    path('sitemap.xml', sitemap_xml),
    path('', include('scorecard.urls')),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
