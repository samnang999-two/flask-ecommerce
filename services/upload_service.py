import os
import uuid
from PIL import Image
from werkzeug.utils import secure_filename

def allowed_file(filename, allowed_extensions):
    return (
        filename
        and '.' in filename
        and filename.rsplit('.', 1)[1].lower() in allowed_extensions
    )

def save_image(file, upload_folder, allowed_extensions, resize_to=(800, 800), thumb_size=(200, 200)):
    if not file or file.filename == '':
        return None

    if not allowed_file(file.filename, allowed_extensions):
        return None

    original_filename = secure_filename(file.filename)
    if not original_filename:
        return None

    name, ext = os.path.splitext(original_filename)
    ext = ext.lower()

    unique_name = uuid.uuid4().hex
    filename = f"{unique_name}{ext}"
    resized_filename = f"{unique_name}_resized{ext}"
    thumbnail_filename = f"{unique_name}_thumb{ext}"

    original_path = os.path.join(upload_folder, filename)
    resized_path = os.path.join(upload_folder, resized_filename)
    thumbnail_path = os.path.join(upload_folder, thumbnail_filename)

    os.makedirs(upload_folder, exist_ok=True)

    try:
        file.save(original_path)

        with Image.open(original_path) as image:
            image.verify()

        with Image.open(original_path) as image:
            if ext in ['.jpg', '.jpeg'] and image.mode not in ['RGB', 'L']:
                image = image.convert('RGB')

            resized = image.copy()
            resized.thumbnail(resize_to, Image.Resampling.LANCZOS)
            resized.save(resized_path)

            thumb = image.copy()
            thumb.thumbnail(thumb_size, Image.Resampling.LANCZOS)
            thumb.save(thumbnail_path)

        return {
            'original': filename,
            'resized': resized_filename,
            'thumbnail': thumbnail_filename
        }

    except Exception:
        for path in [original_path, resized_path, thumbnail_path]:
            if os.path.exists(path):
                try:
                    os.remove(path)
                except OSError:
                    pass
        return None

def delete_image(filename, upload_folder):
    if not filename:
        return

    filename = os.path.basename(filename)
    name, ext = os.path.splitext(filename)

    files = [
        filename,
        f"{name}_resized{ext}",
        f"{name}_thumb{ext}"
    ]

    for file in files:
        file_path = os.path.join(upload_folder, file)
        if os.path.exists(file_path):
            try:
                os.remove(file_path)
            except OSError:
                pass