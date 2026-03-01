from django.contrib import admin
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from unfold.admin import ModelAdmin
from .models import Senator, ParliamentaryPerformance, SenatorQuote


class SenatorQuoteInline(admin.StackedInline):
    model = SenatorQuote
    extra = 1
    fields = ("quote", "date", "order")


@admin.register(Senator)
class SenatorAdmin(ModelAdmin):
    inlines = [SenatorQuoteInline]
    list_display = ('name', 'county', 'nomination', 'party', 'photo_preview', 'image_url')
    search_fields = ('name', 'county', 'nomination', 'party')
    list_filter = ('party', 'county')

    # Group fields logically in the edit form
    fieldsets = (
        ('Basic Info', {
            'fields': ('senator_id', 'name', 'county', 'nomination', 'party', 'available_engines'),
            'description': "For nominated senators: set county to 'Nominated' and fill 'nomination' (e.g. 'Women Affairs Interest').",
        }),
        ('Profile Photo', {
            'fields': ('image', 'photo_preview_large', 'image_url'),
            'description': 'Upload a photo directly, or paste an external URL. '
                           'The uploaded photo takes priority over the URL.',
        }),
    )
    readonly_fields = ('photo_preview_large',)

    def photo_preview(self, obj):
        """Small thumbnail shown in the list view."""
        url = obj.image.url if obj.image else obj.image_url
        if url:
            return format_html(
                '<img src="{}" style="width:40px;height:40px;'
                'object-fit:cover;border-radius:50%;border:2px solid #e2e8f0;" />',
                url,
            )
        return format_html(
            '<div style="width:40px;height:40px;border-radius:50%;'
            'background:linear-gradient(135deg,#ef4444,#dc2626);'
            'display:flex;align-items:center;justify-content:center;'
            'color:white;font-weight:900;font-size:16px;">{}</div>',
            obj.name[0] if obj.name else '?',
        )
    photo_preview.short_description = 'Photo'

    def photo_preview_large(self, obj):
        """Large preview shown in the edit form."""
        url = obj.image.url if obj.image else obj.image_url
        if url:
            return format_html(
                '<img src="{}" style="width:120px;height:120px;'
                'object-fit:cover;object-position:top;border-radius:50%;'
                'border:3px solid #e2e8f0;margin-bottom:8px;" />'
                '<p style="color:#64748b;font-size:12px;margin:0;">'
                'Current photo</p>',
                url,
            )
        return mark_safe('<p style="color:#94a3b8;font-style:italic;">No photo yet</p>')
    photo_preview_large.short_description = 'Preview'


@admin.register(SenatorQuote)
class SenatorQuoteAdmin(ModelAdmin):
    list_display = ("senator", "quote_preview", "date", "order")
    list_filter = ("senator",)
    search_fields = ("quote", "senator__name")
    ordering = ("senator", "order", "-date")

    def quote_preview(self, obj):
        return (obj.quote[:60] + "…") if len(obj.quote) > 60 else obj.quote
    quote_preview.short_description = "Quote"


@admin.register(ParliamentaryPerformance)
class ParliamentaryPerformanceAdmin(ModelAdmin):
    list_display = ('senator', 'speeches', 'attendance_rate', 'sponsored_bills', 'committee_role')
    search_fields = ('senator__name',)
