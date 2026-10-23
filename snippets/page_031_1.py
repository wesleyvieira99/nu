# Interface proposta; não é um cliente Redis completo.
def read_projection(key, cache, source, clock):
    cached = cache.get(key)
    if cached and cached["valid_until"] > clock():
        return {
            "data": cached["data"],
            "origin": "cache",
            "version": cached["version"],
        }
    current = source.read(key)
    cache.set(key, {
        "data": current.data,
        "version": current.version,
        "valid_until": clock() + 15,
    }, ttl_seconds=15)
    return {"data": current.data, "origin": "source",
            "version": current.version}