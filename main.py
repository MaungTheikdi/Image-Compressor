import os
import threading
from tkinter import filedialog, messagebox

import customtkinter as ctk
from PIL import Image


ctk.set_appearance_mode("System")
ctk.set_default_color_theme("blue")

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tif", ".tiff"}


def collect_image_paths(root_dir, exclude_dir=None):
    """Return sorted list of image file paths under root_dir (recursive).

    If exclude_dir is set and lies inside root_dir, files under exclude_dir are skipped
    (so an output folder nested under the source tree is not re-scanned as input).
    """
    paths = []
    root_dir = os.path.normpath(root_dir)
    root_abs = os.path.abspath(root_dir)
    ex_abs = os.path.abspath(exclude_dir) if exclude_dir else None
    ex_prefix = None
    if ex_abs:
        ex_norm = os.path.normcase(ex_abs)
        root_norm = os.path.normcase(root_abs)
        if ex_norm == root_norm or ex_norm.startswith(root_norm + os.sep):
            ex_prefix = ex_norm + os.sep

    for dirpath, _dirnames, filenames in os.walk(root_dir):
        for name in filenames:
            ext = os.path.splitext(name)[1].lower()
            if ext not in IMAGE_EXTENSIONS:
                continue
            full = os.path.join(dirpath, name)
            if ex_prefix and os.path.normcase(os.path.abspath(full)).startswith(ex_prefix):
                continue
            paths.append(full)
    paths.sort()
    return paths


class ImageCompressorApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("Image Compressor Tool")
        self.geometry("640x500")
        self.minsize(660, 560)

        self.input_folder = ""
        self.output_folder = ""
        self.image_paths = []
        self.total_input_size = 0
        self.total_output_size = 0

        self._build_ui()

    def _build_ui(self):
        self.header = ctk.CTkLabel(
            self, text="Image Bulk Compressor", font=("Arial", 24, "bold")
        )
        self.header.pack(pady=(20, 8))

        self.subheader = ctk.CTkLabel(
            self,
            text="Choose source and output folders; all images are compressed into JPEG.",
            text_color="gray60",
        )
        self.subheader.pack(pady=(0, 18))

        self.folder_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.folder_frame.pack(pady=4, padx=20, fill="x")
        self.folder_frame.grid_columnconfigure(0, weight=1, uniform="folder_cols")
        self.folder_frame.grid_columnconfigure(1, weight=1, uniform="folder_cols")

        self.select_input_btn = ctk.CTkButton(
            self.folder_frame, text="Select original images folder", command=self.select_input_folder
        )
        self.select_input_btn.grid(row=0, column=0, sticky="ew", padx=(0, 6), pady=(0, 4))

        self.select_output_btn = ctk.CTkButton(
            self.folder_frame, text="Select output folder", command=self.select_output_folder
        )
        self.select_output_btn.grid(row=0, column=1, sticky="ew", padx=(6, 0), pady=(0, 4))

        self.input_path_label = ctk.CTkLabel(
            self.folder_frame, text="Original: (not set)", anchor="w", wraplength=300
        )
        self.input_path_label.grid(row=1, column=0, sticky="ew", padx=(0, 6), pady=(0, 4))

        self.output_path_label = ctk.CTkLabel(
            self.folder_frame, text="Output: (not set)", anchor="w", wraplength=300
        )
        self.output_path_label.grid(row=1, column=1, sticky="ew", padx=(6, 0), pady=(0, 4))

        self.file_count_label = ctk.CTkLabel(self, text="No folder scanned yet")
        self.file_count_label.pack(pady=(0, 6))

        self.size_info_label = ctk.CTkLabel(self, text="")
        self.size_info_label.pack(pady=(0, 8))

        self.quality_frame = ctk.CTkFrame(self)
        self.quality_frame.pack(padx=20, pady=10, fill="x")

        self.quality_label = ctk.CTkLabel(
            self.quality_frame, text="Compression Quality: 70%"
        )
        self.quality_label.pack(pady=(10, 0))

        self.quality_slider = ctk.CTkSlider(
            self.quality_frame, from_=10, to=95, command=self.update_quality_label
        )
        self.quality_slider.set(70)
        self.quality_slider.pack(padx=16, pady=(8, 12), fill="x")

        self.progress_bar = ctk.CTkProgressBar(self)
        self.progress_bar.set(0)
        self.progress_bar.pack(padx=20, pady=(8, 6), fill="x")

        self.status_label = ctk.CTkLabel(self, text="Ready")
        self.status_label.pack(pady=(0, 16))

        self.compress_btn = ctk.CTkButton(
            self,
            text="Compress & Save",
            fg_color="green",
            hover_color="darkgreen",
            command=self.start_compression_thread,
        )
        self.compress_btn.pack(pady=10)

        self.footer_label = ctk.CTkLabel(
            self,
            text=(
                "Developed by: Theikdi Maung\n"
                "(+95) 09 263 230 440  ·  theidia.ss@gmail.com"
            ),
            font=("Arial", 11),
            text_color="gray55",
            justify="center",
        )
        self.footer_label.pack(pady=(12, 14))

    def _set_path_label(self, label_widget, prefix, path):
        if not path:
            label_widget.configure(text=f"{prefix}: (not set)")
            return
        display = path if len(path) < 80 else f"...{path[-76:]}"
        label_widget.configure(text=f"{prefix}: {display}")

    def update_quality_label(self, value):
        self.quality_label.configure(text=f"Compression Quality: {int(value)}%")

    def _format_bytes(self, size_bytes):
        if size_bytes < 1024:
            return f"{size_bytes} B"
        if size_bytes < 1024 * 1024:
            return f"{size_bytes / 1024:.1f} KB"
        return f"{size_bytes / (1024 * 1024):.2f} MB"

    def select_input_folder(self):
        folder = filedialog.askdirectory(title="Select folder containing original images")
        if not folder:
            return
        self.input_folder = os.path.normpath(folder)
        self._set_path_label(self.input_path_label, "Original", self.input_folder)
        self._refresh_image_list()

    def select_output_folder(self):
        folder = filedialog.askdirectory(title="Select folder to save compressed images")
        if not folder:
            return
        self.output_folder = os.path.normpath(folder)
        self._set_path_label(self.output_path_label, "Output", self.output_folder)
        self.status_label.configure(text="Output folder set")

    def _refresh_image_list(self):
        if not self.input_folder:
            self.image_paths = []
            self.total_input_size = 0
            self.file_count_label.configure(text="No folder scanned yet")
            return
        self.image_paths = collect_image_paths(self.input_folder, self.output_folder)
        self.total_input_size = sum(
            os.path.getsize(p) for p in self.image_paths if os.path.isfile(p)
        )
        n = len(self.image_paths)
        self.file_count_label.configure(text=f"Found: {n} image(s) under original folder")
        self.size_info_label.configure(
            text=f"Input size (scan): {self._format_bytes(self.total_input_size)}"
        )
        self.status_label.configure(text="Ready" if n else "No images found in folder")

    def start_compression_thread(self):
        if not self.input_folder:
            messagebox.showwarning("Warning", "Please select the original images folder.")
            return
        if not self.output_folder:
            messagebox.showwarning("Warning", "Please select the output folder.")
            return
        if not self.image_paths:
            messagebox.showwarning(
                "Warning",
                "No supported images found under the original folder.\n"
                f"(Extensions: {', '.join(sorted(IMAGE_EXTENSIONS))})",
            )
            return

        inp = os.path.normcase(os.path.abspath(self.input_folder))
        out = os.path.normcase(os.path.abspath(self.output_folder))
        if inp == out:
            messagebox.showwarning(
                "Warning",
                "Original and output folders are the same. Choose a different output folder.",
            )
            return

        self.compress_btn.configure(state="disabled")
        self.select_input_btn.configure(state="disabled")
        self.select_output_btn.configure(state="disabled")
        self.progress_bar.set(0)
        self.status_label.configure(text="Compressing...")

        threading.Thread(
            target=self.compress_logic, args=(self.output_folder,), daemon=True
        ).start()

    def compress_logic(self, save_directory):
        quality_val = int(self.quality_slider.get())
        self.total_output_size = 0
        errors = []
        files = list(self.image_paths)
        total = len(files)
        root = self.input_folder

        for index, file_path in enumerate(files, start=1):
            try:
                rel = os.path.relpath(file_path, root)
                rel_dir = os.path.dirname(rel)
                base_name = os.path.splitext(os.path.basename(file_path))[0]
                out_name = f"{base_name}_compressed.jpg"
                out_subdir = (
                    os.path.join(save_directory, rel_dir) if rel_dir else save_directory
                )
                os.makedirs(out_subdir, exist_ok=True)
                output_path = os.path.join(out_subdir, out_name)

                with Image.open(file_path) as img:
                    if img.mode in ("RGBA", "LA", "P"):
                        # Flatten alpha onto white to avoid black background on JPEG export.
                        background = Image.new("RGB", img.size, (255, 255, 255))
                        alpha = img.convert("RGBA")
                        background.paste(alpha, mask=alpha.split()[-1])
                        img = background
                    elif img.mode != "RGB":
                        img = img.convert("RGB")

                    img.thumbnail((800, 800), Image.Resampling.LANCZOS)

                    img.save(output_path, "JPEG", optimize=True, quality=quality_val)
                    self.total_output_size += os.path.getsize(output_path)

            except Exception as exc:
                errors.append(f"{os.path.basename(file_path)}: {exc}")

            progress = index / max(total, 1)
            self.after(0, self.progress_bar.set, progress)
            self.after(
                0,
                self.status_label.configure,
                {"text": f"Compressing... {index}/{total}"},
            )

        self.after(0, self._finish_compression_ui, save_directory, errors)

    def _finish_compression_ui(self, save_directory, errors):
        self.compress_btn.configure(state="normal")
        self.select_input_btn.configure(state="normal")
        self.select_output_btn.configure(state="normal")

        if self.total_input_size > 0:
            saved = self.total_input_size - self.total_output_size
            ratio = (saved / self.total_input_size) * 100
            result_text = (
                f"Input: {self._format_bytes(self.total_input_size)}  |  "
                f"Output: {self._format_bytes(self.total_output_size)}  |  "
                f"Saved: {self._format_bytes(max(saved, 0))} ({max(ratio, 0):.1f}%)"
            )
            self.size_info_label.configure(text=result_text)

        self.progress_bar.set(0)
        self._refresh_image_list()

        if errors:
            self.status_label.configure(text="Finished with some errors")
            short_errors = "\n".join(errors[:8])
            if len(errors) > 8:
                short_errors += f"\n... and {len(errors) - 8} more"
            messagebox.showwarning(
                "Completed with Errors",
                (
                    f"Compressed images were saved in:\n{save_directory}\n\n"
                    f"{len(errors)} file(s) failed:\n{short_errors}"
                ),
            )
            return

        self.status_label.configure(text="Completed successfully")
        messagebox.showinfo(
            "Success", f"Finished! Compressed images saved in:\n{save_directory}"
        )


if __name__ == "__main__":
    app = ImageCompressorApp()
    app.mainloop()
