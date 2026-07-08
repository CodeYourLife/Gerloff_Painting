import logging
from email import policy
from email.utils import getaddresses
from email.parser import BytesParser

from django.conf import settings

logger = logging.getLogger(__name__)


class ExchangeConfigError(Exception):
    pass


class ExchangeFolderNotFound(Exception):
    pass


class UnsupportedEmailFormat(Exception):
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


def _mailboxes(header_value):
    from exchangelib import Mailbox

    mailboxes = []
    for name, email_address in getaddresses([header_value or ""]):
        if email_address:
            mailboxes.append(Mailbox(name=name or None, email_address=email_address))
    return mailboxes


def _message_body(message):
    plain_body = ""
    html_body = ""

    if message.is_multipart():
        for part in message.walk():
            if part.get_content_disposition() == "attachment":
                continue
            content_type = part.get_content_type()
            if content_type == "text/plain":
                plain_body = plain_body or part.get_content()
            elif content_type == "text/html":
                html_body = html_body or part.get_content()
    else:
        if message.get_content_type() == "text/plain":
            plain_body = message.get_content()
        elif message.get_content_type() == "text/html":
            html_body = message.get_content()

    return plain_body.strip(), html_body.strip()


def _message_attachments(message):
    attachments = []

    for part in message.walk():
        if part.get_content_disposition() != "attachment":
            continue

        filename = part.get_filename()
        content = part.get_payload(decode=True)
        if not filename or content is None:
            continue

        attachments.append({"name": filename, "content": content})

    return attachments


def _eml_payload(uploaded_file, content):
    parsed = BytesParser(policy=policy.default).parsebytes(content)
    plain_body, html_body = _message_body(parsed)
    return {
        "subject": str(parsed.get("subject") or uploaded_file.name),
        "author": _mailboxes(str(parsed.get("from", "")))[:1],
        "to_recipients": _mailboxes(str(parsed.get("to", ""))),
        "cc_recipients": _mailboxes(str(parsed.get("cc", ""))),
        "plain_body": plain_body,
        "html_body": html_body,
        "attachments": _message_attachments(parsed),
    }


def _uploaded_email_payload(uploaded_file, content):
    filename = uploaded_file.name.lower()
    if filename.endswith(".eml"):
        return _eml_payload(uploaded_file, content)
    if filename.endswith(".msg"):
        raise UnsupportedEmailFormat(
            ".msg full import is not supported yet. Please save the email as .eml and upload that file."
        )
    raise ValueError("Only .eml files are supported for full email import.")


def file_email_to_job_public_folder(job, uploaded_file):
    from exchangelib import FileAttachment, HTMLBody, Message

    content = uploaded_file.read()
    payload = _uploaded_email_payload(uploaded_file, content)
    account, folder = find_job_public_folder(job.job_number)

    body = HTMLBody(payload["html_body"]) if payload["html_body"] else payload["plain_body"]
    author = payload["author"][0] if payload["author"] else None

    message = Message(
        account=account,
        folder=folder,
        subject=payload["subject"],
        body=body,
        author=author,
        to_recipients=payload["to_recipients"],
        cc_recipients=payload["cc_recipients"],
    )

    for attachment in payload["attachments"]:
        message.attach(
            FileAttachment(name=attachment["name"], content=attachment["content"])
        )

    message.save()

    folder_name = _folder_name(folder)
    logger.info(
        "Filed email to Exchange public folder '%s' for job %s: %s",
        folder_name,
        job.job_number,
        payload["subject"],
    )
    return {"folder_name": folder_name, "subject": payload["subject"]}


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


def list_job_public_folder_emails(job_number, limit=25):
    _, folder = find_job_public_folder(job_number)
    emails = []

    for item in folder.all().order_by("-datetime_received")[:limit]:
        emails.append(
            {
                "subject": item.subject or "(No subject)",
                "sender": str(item.sender or ""),
                "datetime_received": item.datetime_received,
            }
        )

    return _folder_name(folder), emails
