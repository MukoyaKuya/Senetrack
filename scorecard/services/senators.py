from dataclasses import dataclass


def get_frontier(senator):
    """
    Return frontier slug for a senator.

    - Nominated senators (by nomination field or county text) are grouped under "interests".
    - For elected senators, we prefer the normalized County relation and use County.region.
    - If no county link is available, we fall back to "other".
    """
    county_raw = (getattr(senator, "county", "") or "").strip()
    nomination = (getattr(senator, "nomination", "") or "").strip().lower()

    # Nominated / special-interest senators
    if nomination or "nominated" in county_raw.lower():
        return "interests"

    # Prefer explicit FK link to County
    if getattr(senator, "county_fk_id", None):
        # region is a slug like "coast", "rift_valley", etc.
        return getattr(senator.county_fk, "region", "other") or "other"

    return "other"


PLACEHOLDER_NAME = "{{ senator.name }}"
PLACEHOLDER_PARTY = "{{ senator.party }}"


@dataclass
class SenatorDisplay:
    """
    Wrapper used in templates to avoid showing placeholder values
    (e.g., \"{{ senator.name }}\") as literal text, and to attach party logo URL.
    """

    _senator: object
    name: str
    county: str
    party: str
    party_logo_url: str | None

    def __getattr__(self, name):
        return getattr(self._senator, name)


def build_senator_display(senator) -> SenatorDisplay:
    from scorecard.models import Party

    name = (
        senator.senator_id.replace("-", " ").title()
        if getattr(senator, "name", None) == PLACEHOLDER_NAME
        else senator.name
    )
    county = getattr(getattr(senator, "county_fk", None), "name", "—")
    raw_party = getattr(senator, "party", "") or ""
    party = "—" if raw_party == PLACEHOLDER_PARTY else raw_party

    party_logo_url = None
    cleaned_party = raw_party.strip()
    if cleaned_party:
        party_obj = Party.objects.filter(name=cleaned_party, logo__isnull=False).first()
        if party_obj and party_obj.logo:
            try:
                party_logo_url = party_obj.logo.url
            except Exception:
                party_logo_url = None

    return SenatorDisplay(
        _senator=senator,
        name=name,
        county=county,
        party=party,
        party_logo_url=party_logo_url,
    )

