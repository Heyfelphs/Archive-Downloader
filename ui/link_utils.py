from urllib.parse import urlparse

SUPPORTED_SITES = {
    "Fapello": "https://fapello.com",
    "Picazor": "https://picazor.com",
}


def parse_supported_link(text: str):
    value = text.strip()
    if not value or not value.startswith(("http://", "https://")):
        return None
    try:
        parsed = urlparse(value)
    except Exception:
        return None
    host = parsed.netloc.lower()
    if "fapello.com" in host:
        site_label = "Fapello"
    elif "picazor.com" in host:
        site_label = "Picazor"
    else:
        return None
    parts = [p for p in parsed.path.split("/") if p]
    if not parts:
        return None
    if site_label == "Picazor" and parts[0].lower() == "pt" and len(parts) > 1:
        return site_label, parts[1]
    return site_label, parts[0]


def build_url(site_label: str, model_text: str):
    if not model_text:
        return ""
    parsed = parse_supported_link(model_text)
    if parsed:
        site_label, model_text = parsed
    base = SUPPORTED_SITES.get(site_label, "")
    if not base:
        return ""
    model_text = model_text.strip().strip("/")
    if not model_text:
        return ""
    if site_label == "Picazor":
        return f"{base}/pt/{model_text}/"
    return f"{base}/{model_text}/"


def normalize_site_model(site_combo, model_input):
    raw = model_input.text().strip()
    parsed = parse_supported_link(raw)
    if parsed:
        site_label, model = parsed
        site_combo.setCurrentText(site_label)
        model_input.setText(model)
        return site_label, model
    return site_combo.currentText(), raw
