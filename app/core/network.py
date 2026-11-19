from fastapi import Request


def extract_client_ip(request: Request) -> str:
    """Extrae la IP real del cliente respetando cabeceras de proxy inverso (Render/Cloudflare)."""
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()[:64]
    real_ip = request.headers.get("x-real-ip") or request.headers.get("cf-connecting-ip")
    if real_ip:
        return real_ip.strip()[:64]
    if request.client and request.client.host:
        return str(request.client.host)[:64]
    return "127.0.0.1"

