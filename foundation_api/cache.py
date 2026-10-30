from django.core.cache import cache

FOUNDATION_CACHE = "api:v1:foundation"

CACHE_TIMEOUT = 3600


def get_cache(key):
    return cache.get(key)


def set_cache(key, value):
    cache.set(key, value, CACHE_TIMEOUT)


def clear_cache(key):
    cache.delete(key)