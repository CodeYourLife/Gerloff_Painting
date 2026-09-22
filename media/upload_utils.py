import os
import re


def save_uploaded_file_unique(uploaded_file, folder, filename=None):
    os.makedirs(folder, exist_ok=True)

    safe_name = os.path.basename(filename or uploaded_file.name)
    base_name, ext = os.path.splitext(safe_name)
    candidate_name = safe_name
    counter = 1

    while True:
        file_path = os.path.join(folder, candidate_name)
        try:
            with open(file_path, "xb") as destination:
                for chunk in uploaded_file.chunks():
                    destination.write(chunk)
            return candidate_name
        except FileExistsError:
            candidate_name = f"{base_name}_{counter}{ext}"
            counter += 1


def get_requested_upload_filename(uploaded_file, requested_name=None):
    original_name = os.path.basename(uploaded_file.name)
    original_base, original_ext = os.path.splitext(original_name)
    requested_base = os.path.basename((requested_name or "").strip())

    if not requested_base:
        requested_base = original_base

    if original_ext and requested_base.lower().endswith(original_ext.lower()):
        requested_base = requested_base[:-len(original_ext)].strip()

    requested_base = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "", requested_base).strip()
    requested_base = re.sub(r"\s+", " ", requested_base).strip(". ")

    return f"{requested_base or original_base}{original_ext}"
