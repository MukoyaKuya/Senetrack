from django import forms
from .models import ContactMessage, Senator
from . import spam_guard


class ContactMessageForm(forms.ModelForm):
    """
    Feedback / corrections form.

    Security layers baked in (beyond Django's built-in CSRF):
      • Honeypot   — hidden 'website_url' field must stay empty
      • Timing     — 'form_loaded_at' (JS timestamp) must be ≥ 3 s before submit
      • Name       — fake/gibberish name detection
      • Email      — disposable-domain block
      • Subject    — abuse + spam + gibberish checks
      • Body       — abuse + spam + gibberish checks + minimum length
    Rate limiting and duplicate detection are handled in the view.
    """

    # ── Security fields ────────────────────────────────────────────

    # Honeypot: visually hidden; bots fill it, humans don't.
    # Named to look tempting to bots ("website", "url", "phone", etc.)
    website_url = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            "autocomplete": "off",
            "tabindex": "-1",
            "aria-hidden": "true",
        }),
    )

    # Timing: JS fills this with Date.now() on page load.
    form_loaded_at = forms.CharField(
        required=False,
        widget=forms.HiddenInput(),
    )

    # ── Model fields ───────────────────────────────────────────────

    senator_ref = forms.ModelChoiceField(
        queryset=Senator.objects.filter(is_deceased=False).order_by("name"),
        required=False,
        empty_label="— Not senator-specific —",
        label="Related senator (optional)",
    )

    class Meta:
        model = ContactMessage
        fields = ["message_type", "name", "email", "organisation", "subject", "body", "senator_ref"]
        labels = {
            "message_type": "Type of message",
            "name": "Your name",
            "email": "Email address (optional)",
            "organisation": "Organisation / affiliation (optional)",
            "subject": "Subject",
            "body": "Message",
        }
        widgets = {
            "message_type": forms.Select(attrs={"class": "form-select"}),
            "name": forms.TextInput(attrs={"placeholder": "e.g. Jane Wanjiku", "autocomplete": "name"}),
            "email": forms.EmailInput(attrs={"placeholder": "you@example.com", "autocomplete": "email"}),
            "organisation": forms.TextInput(attrs={"placeholder": "e.g. Mzalendo Trust, independent researcher"}),
            "subject": forms.TextInput(attrs={"placeholder": "e.g. Incorrect attendance figure for Sen. X"}),
            "body": forms.Textarea(attrs={
                "rows": 5,
                "placeholder": (
                    "Describe the issue clearly:\n"
                    "• What SENETRACK shows\n"
                    "• What you believe it should show\n"
                    "• Your source / evidence"
                ),
            }),
        }

    # ── Field-level validation ─────────────────────────────────────

    def clean_website_url(self):
        """Honeypot — must be empty. Raise silently-handled error if filled."""
        value = self.cleaned_data.get("website_url", "")
        try:
            spam_guard.check_honeypot(value)
        except spam_guard.SpamError:
            raise forms.ValidationError("__honeypot__")
        return value

    def clean_form_loaded_at(self):
        """Timing check — form must take ≥ 3 s to submit."""
        value = self.cleaned_data.get("form_loaded_at", "")
        try:
            spam_guard.check_timing(value)
        except spam_guard.SpamError as e:
            if "missing" in str(e):
                raise forms.ValidationError("__timing_missing__")
            raise forms.ValidationError("__too_fast__")
        return value

    def clean_name(self):
        name = self.cleaned_data.get("name", "").strip()
        spam_guard.validate_name(name)
        return name

    def clean_email(self):
        email = self.cleaned_data.get("email", "").strip()
        spam_guard.validate_email_domain(email)
        return email

    def clean_subject(self):
        subject = self.cleaned_data.get("subject", "").strip()
        spam_guard.validate_text_content(subject, field_label="Subject")
        return subject

    def clean_body(self):
        body = self.cleaned_data.get("body", "").strip()
        if len(body) < 20:
            raise forms.ValidationError(
                "Please provide a little more detail (at least 20 characters)."
            )
        spam_guard.validate_text_content(body, field_label="Message")
        return body

    # ── Cross-field / non-field validation ─────────────────────────

    def clean(self):
        cleaned = super().clean()

        # Propagate honeypot / timing errors as non-field errors with a generic
        # user-facing message so attackers don't know which check triggered.
        security_errors = {"__honeypot__", "__timing_missing__", "__too_fast__"}
        for field in ("website_url", "form_loaded_at"):
            field_errors = self.errors.get(field, [])
            for err in field_errors:
                if err in security_errors:
                    self.add_error(None, (
                        "Your submission could not be processed. "
                        "Please reload the page and try again."
                    ))
                    # Remove the field-level error so it's not double-shown
                    del self._errors[field]
                    break

        return cleaned
