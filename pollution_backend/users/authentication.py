from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed
from .models import ApiKey

class ApiKeyAuthentication(BaseAuthentication):
    def authenticate(self, request):
        key = request.headers.get('X-API-KEY')
        
        if not key:
            return None

        try:
            api_key = ApiKey.objects.get(key=key)
        except ApiKey.DoesNotExist:
            raise AuthenticationFailed('Nieprawidłowy klucz API')

        if not api_key.is_valid:
            raise AuthenticationFailed('Klucz API wygasł lub jest nieaktywny')

        if api_key.request_count >= api_key.limit:
            raise AuthenticationFailed('Przekroczono limit zapytań dla tego klucza API')

        return (api_key.user, api_key)