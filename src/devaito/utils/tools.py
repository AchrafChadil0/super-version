import bleach


def clean_html(raw_html: str | None) -> str | None:
    if not raw_html:
        return raw_html
    # Strip all tags, leave only text
    return bleach.clean(raw_html, tags=[], strip=True)
