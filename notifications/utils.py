from django.conf import settings
from django.core.mail import EmailMultiAlternatives
import requests


def send_email(to_email: str, subject: str, html_content: str, text_content: str | None = None):
    if not to_email:
        return False
    text = text_content or 'You have a new notification.'
    msg = EmailMultiAlternatives(subject, text, settings.DEFAULT_FROM_EMAIL, [to_email])
    if html_content:
        msg.attach_alternative(html_content, "text/html")
    try:
        msg.send()
        return True
    except Exception:
        return False


def _normalize_msisdn(number: str) -> str:
    if not number:
        return ''
    # Strip non-digits, keep country code if provided
    digits = ''.join(ch for ch in number if ch.isdigit())
    return digits


def send_sms(to_number: str, body: str):
    # Return tuple: (success: bool, meta: dict) for logging
    if not to_number or not body:
        return False, {'error': 'missing_params'}

    username = getattr(settings, 'EBULKSMS_USERNAME', '')
    apikey = getattr(settings, 'EBULKSMS_API_KEY', '')
    sender = getattr(settings, 'EBULKSMS_SENDER', '')
    base_url = getattr(settings, 'EBULKSMS_BASE_URL', 'https://api.ebulksms.com/sendsms.json')
    force_dnd = '1' if getattr(settings, 'EBULKSMS_FORCE_DND', False) else '0'

    if not username or not apikey or not sender:
        return False, {'error': 'missing_credentials'}

    recipient = _normalize_msisdn(to_number)
    if not recipient:
        return False, {'error': 'invalid_recipient'}

    payload = {
        'username': username,
        'apikey': apikey,
        'sender': sender,
        'messagetext': body,
        'recipients': recipient,
        'flash': '0',
        'force_dnd': force_dnd,
    }

    try:
        resp = requests.post(base_url, data=payload, timeout=10)
    except Exception as e:
        return False, {'error': 'request_exception', 'detail': str(e)}

    meta = {
        'status_code': resp.status_code,
        'base_url': base_url,
        'sender': sender,
        'recipients': recipient,
        'force_dnd': force_dnd,
    }

    if resp.status_code != 200:
        meta['response_text'] = (getattr(resp, 'text', '') or '')[:500]
        return False, meta

    # Try to interpret JSON response
    try:
        data = resp.json()
        meta['response_json'] = data
        status = str(data.get('status', '')).lower()
        if 'success' in status or status == 'ok':
            return True, meta
        # Fallback: treat 200 without explicit success as best-effort
        return True, meta
    except Exception:
        # Non-JSON but 200, assume accepted
        meta['response_text'] = (getattr(resp, 'text', '') or '')[:500]
        return True, meta