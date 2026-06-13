import requests    


def normalize_domain(domain: str) -> str:
    domain = domain.strip()
    if not domain.startswith(("http://", "https://")):
        domain = "https://" + domain
    return domain


# print(normalize_domain("https://www.marksandspencer.in/"))



