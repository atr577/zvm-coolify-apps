"""
Custom PAM authentication backend for Django.
Uses python-pam library for system user authentication.

Note: PAM authentication in Docker containers is complex and often doesn't work
because containers don't have access to the host's PAM system. This backend
will attempt PAM authentication, but falls back gracefully if unavailable.
"""
import logging
import os

logger = logging.getLogger(__name__)

# Try to import PAM
PAM_AVAILABLE = False
try:
    import pam
    PAM_AVAILABLE = True
except ImportError:
    logger.warning("python-pam not available. PAM authentication will be disabled.")
except Exception as e:
    logger.warning(f"PAM import error: {e}. PAM authentication will be disabled.")

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
            # Return None to let other backends try
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
                    logger.info(f"Created Django user: {username}")
                
                return user
        except Exception as e:
            # PAM authentication failed or error occurred
            logger.warning(f"PAM authentication failed for {username}: {e}")
            return None
        
        return None
    
    def get_user(self, user_id):
        try:
            return User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return None
