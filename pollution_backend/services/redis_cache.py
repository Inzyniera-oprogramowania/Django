import json
import hashlib
from django.core.cache import cache

DEVICE_LIST_VERSION_KEY = "devices:list:version"
CACHE_TIMEOUT = 60 * 5

class DeviceListCache:
    @staticmethod
    def _get_version() -> int:
        return cache.get_or_set(DEVICE_LIST_VERSION_KEY, 1, timeout=None)

    @staticmethod
    def _generate_key(params: dict) -> str:
        params_with_version = params.copy()
        params_with_version['__v__'] = DeviceListCache._get_version()
        key_base = json.dumps(params_with_version, sort_keys=True)
        key_hash = hashlib.md5(key_base.encode()).hexdigest()
        return f"devices:list:{key_hash}"

    @classmethod
    def get(cls, filter_params: dict):
        key = cls._generate_key(filter_params)
        return cache.get(key)

    @classmethod
    def set(cls, filter_params: dict, data, timeout=CACHE_TIMEOUT):
        key = cls._generate_key(filter_params)
        cache.set(key, data, timeout=timeout)

    @staticmethod
    def invalidate():
        try:
            cache.incr(DEVICE_LIST_VERSION_KEY)
        except ValueError:
            cache.set(DEVICE_LIST_VERSION_KEY, 1, timeout=None)