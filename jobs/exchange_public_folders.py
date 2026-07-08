import logging

from django.conf import settings

logger = logging.getLogger(__name__)


class ExchangeConfigError(Exception):
    pass


class ExchangeFolderNotFound(Exception):
    pass


def _get_required_setting(name):
    value = getattr(settings, name, None)
    if not value:
        raise ExchangeConfigError(f"{name} is not configured.")
    return value


def _folder_name(folder):
    return getattr(folder, "name", None) or getattr(folder, "display_name", "")


def _find_child_folder(parent, expected_name):
    expected_name = expected_name.lower()
    for child in parent.children:
        if _folder_name(child).lower() == expected_name:
            return child
    raise ExchangeFolderNotFound(f"Exchange public folder not found: {expected_name}")


def _get_account():
    try:
        from exchangelib import Account, Configuration, Credentials, DELEGATE
    except ImportError as exc:
        raise ExchangeConfigError("exchangelib is not installed.") from exc

    credentials = Credentials(
        username=_get_required_setting("EXCHANGE_USERNAME"),
        password=_get_required_setting("EXCHANGE_PASSWORD"),
    )
    config = Configuration(
        service_endpoint=_get_required_setting("EXCHANGE_EWS_URL"),
        credentials=credentials,
    )
    return Account(
        primary_smtp_address=_get_required_setting("EXCHANGE_EMAIL"),
        config=config,
        autodiscover=False,
        access_type=DELEGATE,
    )


def find_job_public_folder(job_number):
    account = _get_account()
    open_jobs = _find_child_folder(
        account.public_folders_root,
        getattr(settings, "EXCHANGE_OPEN_JOBS_FOLDER", "Open Jobs"),
    )

    job_prefix = str(job_number).strip().upper()
    for folder in open_jobs.children:
        folder_name = _folder_name(folder).strip()
        if folder_name.upper().startswith(job_prefix):
            return account, folder

    raise ExchangeFolderNotFound(
        f"No Exchange public folder found under Open Jobs for job prefix {job_prefix}."
    )


def copy_exchange_item_to_job_public_folder(item_id, job_number):
    account, folder = find_job_public_folder(job_number)
    item = next(account.fetch(ids=[(item_id, None)]))
    if isinstance(item, Exception):
        raise item

    copy_results = account.bulk_copy(ids=[item], to_folder=folder)
    if copy_results and isinstance(copy_results[0], Exception):
        raise copy_results[0]

    folder_name = _folder_name(folder)
    logger.info(
        "Copied Exchange item to public folder '%s' for job %s: %s",
        folder_name,
        job_number,
        getattr(item, "subject", ""),
    )
    return {
        "folder_name": folder_name,
        "subject": getattr(item, "subject", "") or "(No subject)",
    }


def _mailbox_text(mailbox):
    if not mailbox:
        return ""
    email_address = getattr(mailbox, "email_address", "") or ""
    name = getattr(mailbox, "name", "") or ""
    if name and email_address:
        return f"{name} <{email_address}>"
    return name or email_address or str(mailbox)


def _mailbox_list_text(mailboxes):
    return ", ".join(_mailbox_text(mailbox) for mailbox in (mailboxes or []) if mailbox)


def _attachment_id_value(attachment):
    attachment_id = getattr(attachment, "attachment_id", None)
    return getattr(attachment_id, "id", None) or str(attachment_id or "")


def _attachment_summary(attachment):
    return {
        "id": _attachment_id_value(attachment),
        "name": getattr(attachment, "name", "") or "Attachment",
        "content_type": getattr(attachment, "content_type", "") or "application/octet-stream",
        "size": getattr(attachment, "size", None),
        "is_inline": getattr(attachment, "is_inline", False),
    }


def list_job_public_folder_emails(job_number, limit=50, offset=0):
    _, folder = find_job_public_folder(job_number)
    emails = []

    end = offset + limit + 1
    items = list(folder.all().order_by("-datetime_received")[offset:end])

    for item in items[:limit]:
        emails.append(
            {
                "id": item.id,
                "changekey": item.changekey,
                "subject": item.subject or "(No subject)",
                "sender": _mailbox_text(item.sender),
                "datetime_received": item.datetime_received,
                "has_attachments": item.has_attachments,
            }
        )

    return _folder_name(folder), emails, len(items) > limit


def get_job_public_folder_email(job_number, item_id):
    account, folder = find_job_public_folder(job_number)
    item = next(account.fetch(ids=[(item_id, None)], folder=folder))
    if isinstance(item, Exception):
        raise item

    body = item.body or ""
    text_body = getattr(item, "text_body", None) or ""
    attachments = [
        _attachment_summary(attachment)
        for attachment in (item.attachments or [])
        if getattr(attachment, "name", None)
    ]

    return _folder_name(folder), {
        "id": item.id,
        "subject": item.subject or "(No subject)",
        "sender": _mailbox_text(item.sender),
        "author": _mailbox_text(item.author),
        "to_recipients": _mailbox_list_text(item.to_recipients),
        "cc_recipients": _mailbox_list_text(item.cc_recipients),
        "datetime_received": item.datetime_received,
        "datetime_sent": item.datetime_sent,
        "body": str(body),
        "text_body": str(text_body),
        "body_is_html": body.__class__.__name__ == "HTMLBody",
        "attachments": attachments,
    }


def get_job_public_folder_email_attachment(job_number, item_id, attachment_id):
    account, folder = find_job_public_folder(job_number)
    item = next(account.fetch(ids=[(item_id, None)], folder=folder))
    if isinstance(item, Exception):
        raise item

    for attachment in item.attachments or []:
        if _attachment_id_value(attachment) == attachment_id:
            return {
                "name": getattr(attachment, "name", "") or "attachment",
                "content_type": getattr(attachment, "content_type", "") or "application/octet-stream",
                "content": getattr(attachment, "content", b""),
            }

    raise FileNotFoundError("Attachment was not found on this email.")
