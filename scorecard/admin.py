from django.contrib import admin
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from unfold.admin import ModelAdmin
from .models import Senator, ParliamentaryPerformance, SenatorQuote, County, CountyImage, Party, ContactMessage


class CountyImageInline(admin.StackedInline):
    model = CountyImage
    extra = 1
    fields = ('image', 'caption', 'order')


@admin.register(County)
class CountyAdmin(ModelAdmin):
    inlines = [CountyImageInline]
    list_display = ('name', 'region', 'logo_preview', 'order')
    list_filter = ('region',)
    prepopulated_fields = {'slug': ('name',)}
    fieldsets = (
        ('Basic Info', {
            'fields': ('name', 'slug', 'region', 'order', 'description', 'official_profile_url', 'development_dashboard_url'),
        }),
        ('Logo', {
            'fields': ('logo', 'logo_preview'),
            'description': 'Upload a county logo/crest to display on the county card.',
        }),
        ('Governor', {
            'fields': ('governor_name', 'governor_party', 'governor_image', 'governor_image_preview'),
            'description': "Governor's name, party, and photo shown on the county detail page.",
        }),
        ('Women Representative', {
            'fields': ('women_rep_name', 'women_rep_party', 'women_rep_image'),
            'description': "Women representative's name, party, and photo.",
        }),
    )
    readonly_fields = ('logo_preview', 'governor_image_preview')

    def logo_preview(self, obj):
        if obj and obj.logo:
            return format_html(
                '<img src="{}" style="max-width:120px;max-height:120px;'
                'object-fit:contain;border:1px solid #e2e8f0;border-radius:8px;" />',
                obj.logo.url,
            )
        return mark_safe('<p style="color:#94a3b8;font-style:italic;">No logo yet</p>')
    logo_preview.short_description = 'Preview'

    def governor_image_preview(self, obj):
        if obj and obj.governor_image:
            return format_html(
                '<img src="{}" style="max-width:120px;max-height:120px;'
                'object-fit:cover;border:1px solid #e2e8f0;border-radius:50%%;" />',
                obj.governor_image.url,
            )
        return mark_safe('<p style="color:#94a3b8;font-style:italic;">No governor photo yet</p>')
    governor_image_preview.short_description = 'Preview'


class SenatorQuoteInline(admin.StackedInline):
    model = SenatorQuote
    extra = 1
    fields = ("quote", "date", "order")


@admin.register(Senator)
class SenatorAdmin(ModelAdmin):
    inlines = [SenatorQuoteInline]
    list_display = ('name', 'county_name', 'nomination', 'party', 'photo_preview', 'image_url')
    list_filter = ('party', 'county_fk')

    # Group fields logically in the edit form
    fieldsets = (
        ('Basic Info', {
            'fields': (
                'senator_id',
                'name',
                'county_fk',
                'nomination',
                'party',
                'is_deceased',
                'is_still_computing',
                'is_no_longer_serving',
                'available_engines',
            ),
            'description': (
                "For nominated senators: link the home county (or a generic 'Nominated' county record) and fill "
                "'nomination' (e.g. 'Women Affairs Interest'). Mark 'Still computing' for newly added senators whose "
                "performance data is not yet available. Mark 'No longer serving' for senators who have left the Senate "
                "(e.g. expelled, resigned)."
            ),
        }),
        ('Profile Photo', {
            'fields': ('image', 'photo_preview_large', 'image_url'),
            'description': 'Upload a photo directly, or paste an external URL. '
                           'The uploaded photo takes priority over the URL.',
        }),
    )
    readonly_fields = ('photo_preview_large',)

    def county_name(self, obj):
        return obj.county_fk.name if obj.county_fk else "—"

    county_name.short_description = 'County'
    county_name.admin_order_field = 'county_fk__name'

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
    ordering = ("senator", "order", "-date")

    def quote_preview(self, obj):
        return (obj.quote[:60] + "…") if len(obj.quote) > 60 else obj.quote
    quote_preview.short_description = "Quote"


@admin.register(Party)
class PartyAdmin(ModelAdmin):
    list_display = ('name', 'founded_year', 'leader_name', 'logo_preview')
    fieldsets = (
        (None, {
            'fields': ('name', 'logo', 'logo_preview'),
        }),
        ('Leadership & History', {
            'fields': ('founded_year', 'leader_name', 'history'),
        }),
    )
    readonly_fields = ('logo_preview',)

    def logo_preview(self, obj):
        if obj and obj.logo:
            return format_html(
                '<img src="{}" style="max-width:48px;max-height:48px;'
                'object-fit:contain;border:1px solid #e2e8f0;border-radius:6px;" />',
                obj.logo.url,
            )
        return mark_safe('<span style="color:#94a3b8;font-style:italic;">No logo</span>')
    logo_preview.short_description = 'Logo'


@admin.register(ParliamentaryPerformance)
class ParliamentaryPerformanceAdmin(ModelAdmin):
    list_display = ('senator', 'speeches', 'attendance_rate', 'sponsored_bills', 'committee_role')


@admin.register(ContactMessage)
class ContactMessageAdmin(ModelAdmin):
    list_display = (
        'submitted_at', 'type_badge', 'name', 'email', 'subject_preview',
        'senator_ref', 'status_badge',
    )
    list_filter = ('message_type', 'status', 'submitted_at')
    search_fields = ('name', 'email', 'subject', 'body', 'organisation')
    readonly_fields = ('submitted_at', 'updated_at', 'ip_address')
    ordering = ('-submitted_at',)
    date_hierarchy = 'submitted_at'
    fieldsets = (
        ('Submission', {
            'fields': ('submitted_at', 'message_type', 'status'),
        }),
        ('Sender', {
            'fields': ('name', 'email', 'organisation', 'ip_address'),
        }),
        ('Message', {
            'fields': ('subject', 'body', 'senator_ref'),
        }),
        ('Internal', {
            'fields': ('admin_notes', 'updated_at'),
            'description': 'Internal notes are never shown to the sender.',
        }),
    )

    def subject_preview(self, obj):
        return (obj.subject[:55] + '…') if len(obj.subject) > 55 else obj.subject
    subject_preview.short_description = 'Subject'

    def type_badge(self, obj):
        colours = {
            'data_error':  ('#b91c1c', '#fef2f2'),
            'methodology': ('#1d4ed8', '#eff6ff'),
            'general':     ('#059669', '#ecfdf5'),
            'media':       ('#7c3aed', '#f5f3ff'),
            'other':       ('#475569', '#f8fafc'),
        }
        fg, bg = colours.get(obj.message_type, ('#475569', '#f8fafc'))
        return format_html(
            '<span style="display:inline-block;padding:2px 8px;border-radius:999px;'
            'font-size:11px;font-weight:700;color:{};background:{};">{}</span>',
            fg, bg, obj.get_message_type_display(),
        )
    type_badge.short_description = 'Type'

    def status_badge(self, obj):
        colours = {
            'new':          ('#92400e', '#fffbeb'),
            'under_review': ('#1d4ed8', '#eff6ff'),
            'resolved':     ('#059669', '#ecfdf5'),
            'dismissed':    ('#475569', '#f8fafc'),
        }
        fg, bg = colours.get(obj.status, ('#475569', '#f8fafc'))
        return format_html(
            '<span style="display:inline-block;padding:2px 8px;border-radius:999px;'
            'font-size:11px;font-weight:700;color:{};background:{};">{}</span>',
            fg, bg, obj.get_status_display(),
        )
    status_badge.short_description = 'Status'
