# Creating Django Users (PAM Alternative)

## The Problem
PAM authentication doesn't work in Docker containers because containers don't have access to the host's PAM system. The `python-pam` package is installed but can't authenticate against Ubuntu system users.

## Solution: Create Django Users

Since PAM won't work in Docker, you need to create Django users directly. I've added a management command to make this easy.

### Method 1: Using Management Command (Recommended)

1. **Go to Coolify → Django app → Terminal tab**

2. **Create a user:**
   ```bash
   python manage.py create_user your_username your_password
   ```

3. **Create a superuser (admin):**
   ```bash
   python manage.py create_user admin your_password --superuser
   ```

4. **Now you can log in** with the username and password you created

### Method 2: Using Django Shell

1. **Go to Coolify → Django app → Terminal tab**

2. **Open Django shell:**
   ```bash
   python manage.py shell
   ```

3. **Create a user:**
   ```python
   from django.contrib.auth.models import User
   user = User.objects.create_user('your_username', password='your_password')
   user.save()
   exit()
   ```

### Method 3: Using Django Admin (if you have a superuser)

1. Create a superuser first (Method 1 or 2)
2. Log in at `/admin/`
3. Go to Users section and create users there

## Why PAM Doesn't Work in Docker

Docker containers are isolated from the host system. To use PAM authentication, you would need to:
- Mount `/etc/passwd` and `/etc/shadow` from the host (security risk)
- Mount `/etc/pam.d/` configuration
- Run container with special privileges
- This is complex and not recommended for security reasons

## Recommended Approach

For Docker deployments, use Django's built-in user management:
- Create users via management commands
- Or use Django admin interface
- Or integrate with LDAP/Active Directory if needed
- Or use OAuth/SAML for external authentication

## Quick Start

Run this in the Terminal tab:
```bash
python manage.py create_user admin your_secure_password --superuser
```

Then log in with:
- Username: `admin`
- Password: `your_secure_password`
