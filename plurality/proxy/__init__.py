__all__ = ["ProxyService"]


def __getattr__(name: str):
    if name == "ProxyService":
        from plurality.proxy.service import ProxyService
        return ProxyService
    raise AttributeError(name)