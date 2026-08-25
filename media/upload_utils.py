import os


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
