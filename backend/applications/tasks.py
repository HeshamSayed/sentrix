"""
Celery tasks for automated DNS verification and certificate management
"""

from celery import shared_task
from django.utils import timezone
from datetime import timedelta
import logging

logger = logging.getLogger(__name__)


@shared_task
def auto_verify_dns_records():
    """
    Automatically verify DNS records for all pending applications.
    Runs every 5 minutes to check if DNS has propagated.
    """
    from applications.models import Application
    import dns.resolver
    
    pending_apps = Application.objects.filter(
        traffic_mode='dns',
        dns_status='pending',
        dns_verification_token__isnull=False
    )
    
    verified_count = 0
    
    for app in pending_apps:
        domain = app.protected_domain
        if not domain:
            continue
        
        txt_name = f"_sentrix-verify.{domain}"
        token_ok = False
        cname_ok = False
        
        # Check TXT record
        try:
            answers = dns.resolver.resolve(txt_name, 'TXT')
            for rdata in answers:
                vals = [s.decode('utf-8') if isinstance(s, bytes) else str(s) for s in rdata.strings]
                if app.dns_verification_token in vals:
                    token_ok = True
                    break
        except Exception as e:
            logger.debug(f"TXT check failed for {domain}: {e}")
        
        # Check CNAME record
        try:
            answers = dns.resolver.resolve(domain, 'CNAME')
            for rdata in answers:
                target = str(rdata.target).rstrip('.')
                if target.lower() == (app.edge_hostname or '').lower():
                    cname_ok = True
                    break
        except Exception as e:
            logger.debug(f"CNAME check failed for {domain}: {e}")
        
        # Update status
        if token_ok and cname_ok:
            app.dns_status = 'verified'
            app.save(update_fields=['dns_status'])
            verified_count += 1
            logger.info(f"✅ DNS verified for {domain}")
            
            # Trigger certificate provisioning
            provision_ssl_certificate.delay(str(app.id))
    
    logger.info(f"Auto-verified {verified_count} domains")
    return verified_count


@shared_task
def provision_ssl_certificate(application_id):
    """
    Provision SSL certificate for a verified domain using Let's Encrypt.
    This is a placeholder - in production, integrate with cert-manager or acme.sh
    """
    from applications.models import Application
    
    try:
        app = Application.objects.get(id=application_id)
        if app.dns_status != 'verified':
            logger.warning(f"Cannot provision cert for unverified domain: {app.protected_domain}")
            return
        
        # TODO: Integrate with Let's Encrypt DNS-01 challenge
        # For now, we'll just log it
        logger.info(f"🔐 SSL certificate provisioning initiated for {app.protected_domain}")
        
        # In production, this would:
        # 1. Request cert from Let's Encrypt
        # 2. Create DNS TXT record for _acme-challenge
        # 3. Complete challenge
        # 4. Store cert in database/vault
        # 5. Configure edge to use cert
        
        return True
    except Exception as e:
        logger.error(f"Certificate provisioning failed: {e}")
        return False


@shared_task
def check_application_health():
    """
    Monitor health of all protected applications.
    Used for automatic failover detection.
    """
    from applications.models import Application
    import httpx
    
    verified_apps = Application.objects.filter(
        traffic_mode='dns',
        dns_status='verified',
        is_active=True,
        is_traffic_enabled=True
    )
    
    for app in verified_apps:
        if not app.protected_domain:
            continue
        
        # Check if domain is reachable through SENTRIX Edge
        try:
            url = f"https://{app.edge_hostname}/health"
            response = httpx.get(url, timeout=5.0)
            
            if response.status_code == 200:
                logger.debug(f"✅ Health check OK for {app.protected_domain}")
            else:
                logger.warning(f"⚠️ Health check failed for {app.protected_domain}: {response.status_code}")
        except Exception as e:
            logger.error(f"❌ Health check error for {app.protected_domain}: {e}")


@shared_task
def send_onboarding_notification(user_email, application_name, protected_domain, status):
    """
    Send email notifications during onboarding process.
    """
    # TODO: Integrate with email service (SendGrid, AWS SES, etc.)
    logger.info(f"📧 Email notification: {status} for {application_name} ({protected_domain}) to {user_email}")
    
    # In production, send actual emails:
    # - DNS records added
    # - DNS verification in progress
    # - DNS verified successfully
    # - SSL certificate provisioned
    # - Application is now protected
    
    return True


@shared_task
def cleanup_expired_verification_tokens():
    """
    Clean up applications with expired verification tokens (7 days old).
    """
    from applications.models import Application
    
    cutoff = timezone.now() - timedelta(days=7)
    
    expired = Application.objects.filter(
        traffic_mode='dns',
        dns_status='pending',
        created_at__lt=cutoff
    )
    
    count = expired.count()
    if count > 0:
        # Reset to allow retry
        expired.update(
            dns_verification_token='',
            dns_status='failed'
        )
        logger.info(f"Cleaned up {count} expired verification tokens")
    
    return count

