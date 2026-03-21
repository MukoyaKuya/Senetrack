# Security

Summary of security measures and deployment checklist for the Kenya Senate Scorecard.

## What’s in place

### Application

- **Input validation**  
  - **Senator IDs** (URL and compare): only `[a-zA-Z0-9_-]`, max 50 chars. Invalid IDs get 404.  
  - **County slugs**: only `[a-z0-9-]`, max 60 chars. Invalid slug → 404.  
  - **Compare `ids`** (GET): sanitized and capped at 5.  
  - **Insights/frontier filters** (party, frontier, county): sanitized length and charset; county must match slug format.  
  - **Engine type** (HTMX partial): allowlist (`parliamentary`); anything else treated as unknown.

- **Templates**  
  - Django auto-escapes output; admin uses `format_html` for known URLs and `mark_safe` only for static strings (no user-controlled content marked safe).

- **CSRF**  
  - `CsrfViewMiddleware` enabled; use `{% csrf_token %}` on forms and CSRF token for AJAX where applicable.

- **SQL**  
  - No raw SQL with string interpolation; ORM and parameterized queries only.

### Settings (production)

When `DEBUG=False`:

- **SECRET_KEY**  
  - Must be set via `DJANGO_SECRET_KEY`; the default insecure key is rejected and the app will not start.

- **ALLOWED_HOSTS**  
  - Must be set (e.g. your domain). Empty list is rejected.

- **Headers and cookies**  
  - `SECURE_BROWSER_XSS_FILTER`, `SECURE_CONTENT_TYPE_NOSNIFF`, `X_FRAME_OPTIONS=DENY`.  
  - `SESSION_COOKIE_HTTPONLY`, `SESSION_COOKIE_SAMESITE=Lax`, `CSRF_COOKIE_SAMESITE=Lax`.  
  - If `SECURE_SSL_REDIRECT` is not disabled via env: `SECURE_SSL_REDIRECT`, `SESSION_COOKIE_SECURE`, `CSRF_COOKIE_SECURE`, HSTS (1 year, include subdomains, preload).

### Optional: SSL redirect in production

To disable HTTPS redirect (e.g. behind a reverse proxy that terminates SSL), set:

```bash
SECURE_SSL_REDIRECT=false
```

## Deployment checklist

1. Set **`DJANGO_SECRET_KEY`** to a long random value (e.g. `python -c "import secrets; print(secrets.token_urlsafe(50))"`).
2. Set **`DJANGO_DEBUG=false`**.
3. Set **`ALLOWED_HOSTS`** to your domain(s), e.g. `yourdomain.com,www.yourdomain.com`.
4. Use HTTPS; ensure the front proxy or load balancer terminates SSL if you set `SECURE_SSL_REDIRECT=false`.
5. Do not commit **`.env`** or any file containing secrets; keep **`SECRET_KEY`** and **`DATABASE_URL`** in env only.
6. Restrict **admin** access (strong passwords, limit by IP if needed).
7. Keep dependencies updated (e.g. `pip list --outdated`, `pip-audit` or similar).

## Optional hardening

- **Rate limiting**  
  - For high-traffic or public endpoints (e.g. compare, insights), consider `django-ratelimit` or reverse-proxy rate limits to reduce abuse and DoS risk.

- **Content-Security-Policy (CSP)**  
  - Add a CSP header (via middleware or proxy) if you want to restrict script/source origins; test to avoid breaking inline scripts or third-party assets.

- **File uploads (admin)**  
  - Django’s `ImageField` does not restrict file type by default. For stricter safety, add a custom validator or use a library (e.g. `python-magic`) to validate uploads; see Django’s [FileField validation](https://docs.djangoproject.com/en/stable/ref/models/fields/#filefield).

- **Security headers**  
  - Permissions-Policy (formerly Feature-Policy) can be set in the reverse proxy or via middleware to disable unneeded features (camera, geolocation, etc.).

## Reporting issues

If you discover a security vulnerability, report it privately (e.g. to the maintainers or via a private channel) rather than in a public issue.
