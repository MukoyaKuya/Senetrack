from django import template

register = template.Library()

# Grade -> (bar color hex, badge bg hex, badge text hex)
GRADE_STYLES = {
    "A": ("#14532d", "#dcfce7", "#14532d"),
    "A-": ("#16a34a", "#bbf7d0", "#15803d"),
    "B+": ("#1d4ed8", "#dbeafe", "#1d4ed8"),
    "B": ("#3b82f6", "#bfdbfe", "#2563eb"),
    "B-": ("#0ea5e9", "#e0f2fe", "#0369a1"),
    "C+": ("#c2410c", "#ffedd5", "#c2410c"),
    "C": ("#ea580c", "#fed7aa", "#c2410c"),
    "C-": ("#fb923c", "#fde8c8", "#9a3412"),
    "D+": ("#1F0954", "#ede9fe", "#1F0954"),
    "D": ("#6F00FE", "#ede9fe", "#6F00FE"),
    "D-": ("#32127A", "#f5f3ff", "#32127A"),
    "E": ("#dc2626", "#fee2e2", "#dc2626"),
    "NEW": ("#94a3b8", "#f1f5f9", "#475569"),
}


@register.filter
def get_item(d, key):
    """Look up key in a dict (e.g. for variable key in template)."""
    if not isinstance(d, dict):
        return None
    return d.get(key)


@register.filter
def replace_underscore(value):
    """Replace underscores with spaces and title-case. For region display."""
    return (value or "").replace("_", " ").title()


@register.simple_tag
def grade_bar_color(grade):
    """Return the bar color hex for a grade."""
    return GRADE_STYLES.get(grade, ("#e2e8f0", "#f1f5f9", "#64748b"))[0]


@register.simple_tag
def grade_badge_style(grade):
    """Return inline style string for grade badge (background and color)."""
    styles = GRADE_STYLES.get(grade, ("#e2e8f0", "#f1f5f9", "#64748b"))
    return f"background:{styles[1]};color:{styles[2]};"


@register.filter
def thumb(url, params):
    """
    Append Cloudinary transformation parameters to a URL.
    Usage: {{ image.url|thumb:"w_128,h_128,c_fill" }}
    Resolves local media URLs to Cloudinary when in production (DEBUG=False).
    """
    if not url:
        return ""
        
    url_str = str(url)
    from django.conf import settings
    
    # In production, if it's a local media URL, resolve to Cloudinary
    if url_str.startswith('/media/') and not settings.DEBUG:
        cloud_name = settings.CLOUDINARY_STORAGE.get('CLOUD_NAME', 'dlj4gpozf')
        relative_path = url_str.replace('/media/', '')
        resolved_url = f"https://res.cloudinary.com/{cloud_name}/image/upload/{relative_path}"
        # print(f"DEBUG: Resolved {url_str} to {resolved_url}")
        url_str = resolved_url
    else:
        # print(f"DEBUG: Skipping resolution for {url_str}. DEBUG={settings.DEBUG}")
        pass
    
    # Check if this is a Cloudinary URL
    if "res.cloudinary.com" in url_str:
        # Standard transformations for speed and size
        base_params = "f_auto,q_auto"
        # Combine with user params
        all_params = f"{base_params},{params}"
        
        # Inject params after /upload/
        if "/upload/" in url_str:
            return url_str.replace("/upload/", f"/upload/{all_params}/")
            
    return url_str
