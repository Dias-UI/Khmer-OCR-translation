import os
import re
import time
import tempfile
import tkinter as tk
from tkinter import filedialog, messagebox

import fitz  # PyMuPDF
import pytesseract
from PIL import Image, ImageEnhance, ImageFilter
from deep_translator import GoogleTranslator
from tkinterdnd2 import DND_FILES, TkinterDnD


current_text = {"original": "", "translated": ""}
current_page = 0
total_pages = 0
pdf_pages = []
current_lang = None
current_file = None


def clean_text(text, lang):
    if "khm" in lang:
        text = re.sub(r"[^\u1780-\u17FF\u19E0-\u19FF\u0020-\u007E\n\r\t]", "", text)
    text = re.sub(r"\n\s*\n", "\n\n", text)
    text = re.sub(r" +", " ", text)
    return text.strip()


def preprocess_image(image):
    image = image.convert("L")
    image = image.filter(ImageFilter.MedianFilter(size=3))
    image = ImageEnhance.Contrast(image).enhance(2.5)
    image = ImageEnhance.Sharpness(image).enhance(2.0)
    image = image.point(lambda p: 255 if p > 128 else 0)
    return image


def translate_text(text, source, target):
    if not text.strip():
        return ""

    translator = GoogleTranslator(source=source, target=target)
    chunk_size = 1000
    chunks = [text[i:i + chunk_size] for i in range(0, len(text), chunk_size)]
    translated = []

    for i, chunk in enumerate(chunks):
        status_label.config(text=f"Translating chunk {i + 1}/{len(chunks)}...")
        root.update_idletasks()

        if not chunk.strip():
            continue

        for attempt in range(3):
            try:
                time.sleep(1.5)
                result = translator.translate(chunk)
                translated.append(result if result else chunk)
                break
            except Exception:
                if attempt == 2:
                    translated.append(chunk)
                else:
                    time.sleep(4)

    return "\n".join(translated)


def get_translation_direction(lang):
    if lang == "eng":
        return "en", "km"
    return "km", "en"


def save_outputs():
    if not current_file or not current_text["original"].strip():
        messagebox.showwarning("Nothing to save", "No processed text available.")
        return

    directory = os.path.dirname(current_file)
    name = os.path.splitext(os.path.basename(current_file))[0]

    original_path = os.path.join(directory, f"{name}_original.txt")
    translated_path = os.path.join(directory, f"{name}_translated.txt")

    with open(original_path, "w", encoding="utf-8") as f:
        f.write(current_text["original"])

    with open(translated_path, "w", encoding="utf-8") as f:
        f.write(current_text["translated"])

    messagebox.showinfo(
        "Saved",
        f"Original saved to:\n{original_path}\n\nTranslation saved to:\n{translated_path}"
    )


def toggle_language():
    shown = text_widget.get("1.0", tk.END).strip()
    if shown == current_text["original"].strip():
        text_widget.delete("1.0", tk.END)
        text_widget.insert(tk.END, current_text["translated"])
        toggle_button.config(text="Show Original")
    else:
        text_widget.delete("1.0", tk.END)
        text_widget.insert(tk.END, current_text["original"])
        toggle_button.config(text="Show Translation")


def update_page_label():
    if total_pages > 0:
        page_label.config(text=f"Page {current_page + 1} of {total_pages}")
        prev_button.config(state=tk.NORMAL if current_page > 0 else tk.DISABLED)
        next_button.config(state=tk.NORMAL if current_page < total_pages - 1 else tk.DISABLED)
        page_nav_frame.pack(pady=5)
    else:
        page_nav_frame.pack_forget()


def process_pdf_page(page_num, lang):
    global current_page, current_text

    try:
        current_page = page_num
        image = preprocess_image(pdf_pages[page_num])

        extracted = pytesseract.image_to_string(
            image,
            lang=lang,
            config="--psm 6"
        )

        extracted = clean_text(extracted, lang)
        source, target = get_translation_direction(lang)
        translated = translate_text(extracted, source, target)

        current_text["original"] = extracted
        current_text["translated"] = translated

        text_widget.delete("1.0", tk.END)
        text_widget.insert(tk.END, extracted)

        toggle_button.pack(pady=5)
        save_button.pack(pady=5)
        toggle_button.config(text="Show Translation")
        update_page_label()
        status_label.config(text="Done")

    except Exception as e:
        messagebox.showerror("Error", f"Error processing page {page_num + 1}: {e}")


def load_pdf(filepath, lang):
    global pdf_pages, total_pages, current_page, current_lang, current_file

    try:
        current_file = filepath
        current_lang = lang
        pdf_pages = []

        status_label.config(text="Loading PDF...")
        root.update_idletasks()

        doc = fitz.open(filepath)
        total_pages = len(doc)

        for page_num in range(total_pages):
            page = doc[page_num]
            pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))
            img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
            pdf_pages.append(img)

        doc.close()

        current_page = 0
        process_pdf_page(0, lang)

    except Exception as e:
        messagebox.showerror("Error", f"Error loading PDF: {e}")


def process_image(lang, filepath=None):
    global pdf_pages, total_pages, current_page, current_lang, current_file, current_text

    try:
        if filepath is None:
            filepath = filedialog.askopenfilename(
                filetypes=[
                    ("Supported Files", "*.jpg;*.jpeg;*.png;*.bmp;*.pdf"),
                    ("Images", "*.jpg;*.jpeg;*.png;*.bmp"),
                    ("PDF Files", "*.pdf")
                ]
            )

        if not filepath:
            return

        current_file = filepath
        current_lang = lang

        if filepath.lower().endswith(".pdf"):
            load_pdf(filepath, lang)
            return

        pdf_pages = []
        total_pages = 0
        current_page = 0
        update_page_label()

        status_label.config(text="Processing image...")
        root.update_idletasks()

        image = preprocess_image(Image.open(filepath))
        extracted = pytesseract.image_to_string(
            image,
            lang=lang,
            config="--psm 6"
        )

        extracted = clean_text(extracted, lang)
        source, target = get_translation_direction(lang)
        translated = translate_text(extracted, source, target)

        current_text["original"] = extracted
        current_text["translated"] = translated

        text_widget.delete("1.0", tk.END)
        text_widget.insert(tk.END, extracted)

        toggle_button.pack(pady=5)
        save_button.pack(pady=5)
        toggle_button.config(text="Show Translation")
        status_label.config(text="Done")

    except Exception as e:
        messagebox.showerror("Error", str(e))


def navigate_page(direction):
    new_page = max(0, min(current_page + direction, total_pages - 1))
    process_pdf_page(new_page, current_lang)


def handle_drop(event, lang):
    file_path = event.data.strip("{}")
    if file_path:
        process_image(lang, file_path)
    event.widget.configure(bg="#303030")


def handle_drag_enter(event):
    event.widget.configure(bg="#505050")


def handle_drag_leave(event):
    event.widget.configure(bg="#303030")


root = TkinterDnD.Tk()
root.title("Khmer / English OCR Translator")
root.geometry("760x650")
root.configure(bg="#121212")

title_label = tk.Label(
    root,
    text="Khmer / English OCR Translator",
    font=("Arial", 20),
    fg="white",
    bg="#121212"
)
title_label.pack(pady=10)

button_frame = tk.Frame(root, bg="#121212")
button_frame.pack(pady=10)

khmer_button = tk.Button(
    button_frame,
    text="Khmer → English",
    command=lambda: process_image("khm"),
    bg="#303030",
    fg="white",
    width=18,
    height=2,
    font=("Helvetica", 12)
)
khmer_button.pack(side=tk.LEFT, padx=8)

english_button = tk.Button(
    button_frame,
    text="English → Khmer",
    command=lambda: process_image("eng"),
    bg="#303030",
    fg="white",
    width=18,
    height=2,
    font=("Helvetica", 12)
)
english_button.pack(side=tk.LEFT, padx=8)

mixed_button = tk.Button(
    button_frame,
    text="Mixed Khmer/English",
    command=lambda: process_image("khm+eng"),
    bg="#303030",
    fg="white",
    width=20,
    height=2,
    font=("Helvetica", 12)
)
mixed_button.pack(side=tk.LEFT, padx=8)

page_nav_frame = tk.Frame(root, bg="#121212")

prev_button = tk.Button(
    page_nav_frame,
    text="◀ Previous",
    command=lambda: navigate_page(-1),
    bg="#303030",
    fg="white",
    width=12
)
prev_button.pack(side=tk.LEFT, padx=5)

page_label = tk.Label(
    page_nav_frame,
    text="",
    font=("Arial", 10),
    fg="white",
    bg="#121212"
)
page_label.pack(side=tk.LEFT, padx=10)

next_button = tk.Button(
    page_nav_frame,
    text="Next ▶",
    command=lambda: navigate_page(1),
    bg="#303030",
    fg="white",
    width=12
)
next_button.pack(side=tk.LEFT, padx=5)

text_widget = tk.Text(
    root,
    wrap=tk.WORD,
    font=("Arial", 12),
    bg="#303030",
    fg="white",
    insertbackground="white"
)
text_widget.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

scrollbar = tk.Scrollbar(text_widget)
scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
text_widget.config(yscrollcommand=scrollbar.set)
scrollbar.config(command=text_widget.yview)

toggle_button = tk.Button(
    root,
    text="Show Translation",
    command=toggle_language,
    bg="#303030",
    fg="white",
    width=18
)
toggle_button.pack_forget()

save_button = tk.Button(
    root,
    text="Save Text Files",
    command=save_outputs,
    bg="#303030",
    fg="white",
    width=18
)
save_button.pack_forget()

status_label = tk.Label(
    root,
    text="Drag a PDF/image onto a button or click a button to select a file.",
    font=("Arial", 9, "italic"),
    fg="#808080",
    bg="#121212"
)
status_label.pack(pady=(0, 10))

for btn, lng in [
    (khmer_button, "khm"),
    (english_button, "eng"),
    (mixed_button, "khm+eng"),
]:
    btn.drop_target_register(DND_FILES)
    btn.dnd_bind("<<Drop>>", lambda e, l=lng: handle_drop(e, l))
    btn.dnd_bind("<<DragEnter>>", handle_drag_enter)
    btn.dnd_bind("<<DragLeave>>", handle_drag_leave)

root.mainloop()
