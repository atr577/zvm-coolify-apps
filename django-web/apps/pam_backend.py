"""
Custom PAM authentication backend for Django.
Uses python-pam library for system user authentication.
"""
import logging

logger = logging.getLogger(__name__)

try:
    import pam
    PAM_AVAILABLE = True
except ImportError:
    PAM_AVAILABLE = False
    logger.warning("python-pam not available. PAM authentication will be disabled.")


from django.contrib.auth.backends import BaseBackend
from django.contrib.auth.models import User


class PAMBackend(BaseBackend):
    """
    Authenticate using PAM (Pluggable Authentication Modules).
    This allows authentication against Ubuntu system users.
    
    Note: PAM may not work in Docker containers. In that case, 
    authentication will fall back to Django's default backend.
    """
    
    def authenticate(self, request, username=None, password=None, **kwargs):
        if username is None or password is None:
            return None
        
        if not PAM_AVAILABLE:
            logger.debug("PAM not available, skipping PAM authentication")
            return None
        
        try:
            # Authenticate with PAM
            p = pam.pam()
            if p.authenticate(username, password):
                # Get or create Django user
                try:
                    user = User.objects.get(username=username)
                except User.DoesNotExist:
                    # Create new user if doesn't exist
                    user = User(username=username)
                    user.set_unusable_password()  # Don't store password in Django
                    user.save()
                
                return user
        except Exception as e:
            # PAM authentication failed or error occurred
            logger.debug(f"PAM authentication failed: {e}")
            return None
        
        return None
    
    def get_user(self, user_id):
        try:
            return User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return None
