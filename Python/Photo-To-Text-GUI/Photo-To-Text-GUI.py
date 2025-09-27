import os
import sys
import time
import warnings
from pathlib import Path

# Suppress HF progress bars and warnings
os.environ["HF_HUB_DISABLE_SYMLINKS_WARNING"] = "1"
os.environ["TRANSFORMERS_NO_ADVISORY_WARNINGS"] = "1"
os.environ["HF_HUB_DISABLE_PROGRESS_BARS"] = "1"
warnings.filterwarnings("ignore")

from PIL import Image
import pytesseract

# Default tesseract path for Windows users, update if needed
DEFAULT_TESSERACT = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
if os.name == 'nt' and Path(DEFAULT_TESSERACT).exists():
    pytesseract.pytesseract.tesseract_cmd = DEFAULT_TESSERACT

# Attempt to import optional AI libs
USE_AI = False
MODEL_DIR = Path("blip_model")
try:
    from transformers import BlipProcessor, BlipForConditionalGeneration, logging as hf_logging
    import torch

    hf_logging.set_verbosity_error()
    USE_AI = True
except Exception:
    USE_AI = False

# PyQt6 UI
from PyQt6.QtWidgets import (
    QApplication, QWidget, QLabel, QPushButton, QVBoxLayout, QHBoxLayout,
    QTextEdit, QFileDialog, QProgressBar, QCheckBox, QMessageBox, QSizePolicy
)
from PyQt6.QtGui import QPixmap, QIcon
from PyQt6.QtCore import Qt, QThread, pyqtSignal


class OCRWorker(QThread):
    progress = pyqtSignal(int)
    status = pyqtSignal(str)
    finished = pyqtSignal(str)

    def __init__(self, image_path: str, enable_ai: bool = False):
        super().__init__()
        self.image_path = image_path
        self.enable_ai = enable_ai and USE_AI
        # model handles (shared globals loaded on demand)
        self._processor = None
        self._model = None

    def run(self):
        try:
            self.status.emit('Running OCR...')
            self.progress.emit(5)
            # small pause for UI feel
            time.sleep(0.15)

            img = Image.open(self.image_path)
            text = pytesseract.image_to_string(img, lang='eng').strip()
            self.progress.emit(60)

            if text:
                self.status.emit('Text detected by OCR')
                self.progress.emit(95)
                time.sleep(0.1)
                self.finished.emit(text)
                return

            # If no text and AI enabled, run caption model
            if self.enable_ai:
                self.status.emit('No OCR text, preparing AI...')
                # ensure model loaded (this will download if needed)
                ok = self._ensure_model_loaded()
                if not ok:
                    self.status.emit('AI initialization failed')
                    self.finished.emit('')
                    return

                self.status.emit('Generating AI description...')
                self.progress.emit(70)

                # Prepare inputs
                image_rgb = Image.open(self.image_path).convert('RGB')
                inputs = self._processor(image_rgb, return_tensors='pt')

                # Move to GPU if available
                device = 'cuda' if torch.cuda.is_available() else 'cpu'
                try:
                    self._model.to(device)
                    inputs = {k: v.to(device) for k, v in inputs.items()}
                except Exception:
                    device = 'cpu'

                out = self._model.generate(**inputs, max_length=120, num_beams=3, early_stopping=True)
                desc = self._processor.decode(out[0], skip_special_tokens=True)
                self.progress.emit(98)
                time.sleep(0.1)
                self.finished.emit(desc)
                return

            # fallback: no text and AI disabled
            self.status.emit('No text found, AI disabled')
            self.progress.emit(100)
            self.finished.emit('')

        except Exception as e:
            self.status.emit(f'Error: {e}')
            self.finished.emit('')

    def _ensure_model_loaded(self) -> bool:
        global USE_AI, MODEL_DIR
        try:
            # If already loaded globally, use global instances
            from __main__ import BLIP_PROCESSOR, BLIP_MODEL
            if BLIP_PROCESSOR is not None and BLIP_MODEL is not None:
                self._processor = BLIP_PROCESSOR
                self._model = BLIP_MODEL
                self.progress.emit(65)
                return True
        except Exception:
            pass

        try:
            # If local cache exists, load from directory
            if MODEL_DIR.exists():
                self.status.emit('Loading cached AI model...')
                self.progress.emit(30)
                proc = BlipProcessor.from_pretrained(str(MODEL_DIR), use_fast=True)
                model = BlipForConditionalGeneration.from_pretrained(str(MODEL_DIR))
                self._processor = proc
                self._model = model
                # store globally
                try:
                    globals()['BLIP_PROCESSOR'] = proc
                    globals()['BLIP_MODEL'] = model
                except Exception:
                    pass
                self.progress.emit(60)
                return True

            # Otherwise download with friendly progress updates
            self.status.emit('Downloading AI model (this may take time)...')
            # fake progress while HF downloads in background
            for p in range(10, 55, 10):
                self.progress.emit(p)
                time.sleep(0.25)

            proc = BlipProcessor.from_pretrained('Salesforce/blip-image-captioning-base', use_fast=True)
            self.progress.emit(60)
            model = BlipForConditionalGeneration.from_pretrained('Salesforce/blip-image-captioning-base')
            self.progress.emit(80)

            # attempt to cache locally
            try:
                MODEL_DIR.mkdir(exist_ok=True)
                proc.save_pretrained(str(MODEL_DIR))
                model.save_pretrained(str(MODEL_DIR))
            except Exception:
                # cache failure is non-fatal
                pass

            self._processor = proc
            self._model = model
            try:
                globals()['BLIP_PROCESSOR'] = proc
                globals()['BLIP_MODEL'] = model
            except Exception:
                pass

            self.progress.emit(90)
            return True

        except Exception as e:
            self.status.emit(f'AI load error: {e}')
            return False

class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('Photo-To-Text GUI')
        self.setWindowIcon(QIcon("PTT.ico"))
        self.resize(940, 640)
        self._build_ui()
        self.worker = None

        # Apply the theme here
        self.apply_theme()  # call instance method

    def apply_theme(self):
        self.setStyleSheet(''' 
        QWidget { background-color: #1e1e2f; color: #c5c8c6; font-family: 'Segoe UI'; font-size: 14px; }
        QPushButton { background-color: #3a3a5a; color: #fff; border-radius: 5px; padding: 5px 10px; }
        QPushButton:hover { background-color: #50507a; }
        QLabel { color: #61dafb; }
        QTextEdit { background-color: #2b2b3f; color: #f8f8f2; border: 1px solid #44475a; border-radius: 4px; }
        QProgressBar { border: 1px solid #44475a; border-radius: 4px; text-align: center; color: #fff; }
        QProgressBar::chunk { background-color: #6272a4; }
        QCheckBox { spacing: 5px; }
        QCheckBox::indicator { width: 15px; height: 15px; }
        QCheckBox::indicator:checked { background-color: #50fa7b; border: 1px solid #44475a; }
        ''')

    def _build_ui(self):
        layout = QVBoxLayout()

        # Top controls
        top = QHBoxLayout()
        self.btn_open = QPushButton('Open Image')
        self.btn_open.clicked.connect(self.open_image)
        top.addWidget(self.btn_open)

        self.chk_ai = QCheckBox('Enable Local AI (heavy)')
        self.chk_ai.setToolTip('Use local BLIP model for image description when OCR fails')
        self.chk_ai.setEnabled(USE_AI)
        top.addWidget(self.chk_ai)

        self.btn_process = QPushButton('Process')
        self.btn_process.clicked.connect(self.on_process)
        top.addWidget(self.btn_process)

        self.btn_save = QPushButton('Save Output')
        self.btn_save.clicked.connect(self.on_save)
        top.addWidget(self.btn_save)

        layout.addLayout(top)

        # Middle: image preview + text
        mid = QHBoxLayout()

        self.lbl_image = QLabel('No image loaded')
        self.lbl_image.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_image.setFixedWidth(460)
        self.lbl_image.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Expanding)
        mid.addWidget(self.lbl_image)

        self.txt_output = QTextEdit()
        self.txt_output.setPlaceholderText('OCR or AI output will appear here')
        mid.addWidget(self.txt_output)

        layout.addLayout(mid)

        # Bottom: progress and status
        bottom = QHBoxLayout()
        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        bottom.addWidget(self.progress)

        self.lbl_status = QLabel('Idle')
        bottom.addWidget(self.lbl_status)

        layout.addLayout(bottom)

        self.setLayout(layout)

    def open_image(self):
        path, _ = QFileDialog.getOpenFileName(self, 'Open image', '', 'Images (*.png *.jpg *.jpeg *.bmp *.gif)')
        if not path:
            return
        self.image_path = path
        pix = QPixmap(path)
        if pix.width() > 440:
            pix = pix.scaledToWidth(440, Qt.TransformationMode.SmoothTransformation)
        self.lbl_image.setPixmap(pix)
        self.lbl_status.setText(f'Image loaded: {path}')

    def on_process(self):
        if not hasattr(self, 'image_path') or not self.image_path:
            QMessageBox.warning(self, 'No image', 'Please open an image first')
            return

        # If AI is enabled and cached model exists, ask whether to reuse
        use_ai = self.chk_ai.isChecked()
        if use_ai and USE_AI and MODEL_DIR.exists():
            resp = QMessageBox.question(self, 'Cached model', 'A cached AI model exists. Reuse cached model?\nChoose No to redownload',
                                        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, QMessageBox.StandardButton.Yes)
            # if No and user chose No -> delete cache to force re-download
            if resp == QMessageBox.StandardButton.No:
                try:
                    import shutil
                    shutil.rmtree(str(MODEL_DIR))
                except Exception:
                    pass

        # disable UI controls
        self.btn_process.setEnabled(False)
        self.btn_open.setEnabled(False)
        self.chk_ai.setEnabled(False)
        self.progress.setValue(0)
        self.lbl_status.setText('Starting processing...')
        self.txt_output.clear()

        self.worker = OCRWorker(self.image_path, enable_ai=use_ai)
        self.worker.progress.connect(self.progress.setValue)
        self.worker.status.connect(self.lbl_status.setText)
        self.worker.finished.connect(self._on_finished)
        self.worker.start()

    def _on_finished(self, text: str):
        self.txt_output.setPlainText(text)
        self.lbl_status.setText('Finished')
        self.progress.setValue(100)
        self.btn_process.setEnabled(True)
        self.btn_open.setEnabled(True)
        self.chk_ai.setEnabled(USE_AI)

    def on_save(self):
        txt = self.txt_output.toPlainText()
        if not txt:
            QMessageBox.information(self, 'No output', 'There is no output to save')
            return
        path, _ = QFileDialog.getSaveFileName(self, 'Save output', 'output.txt', 'Text Files (*.txt)')
        if not path:
            return
        try:
            with open(path, 'w', encoding='utf-8') as f:
                f.write(txt)
            QMessageBox.information(self, 'Saved', f'Saved to {path}')
        except Exception as e:
            QMessageBox.critical(self, 'Error', f'Failed to save: {e}')

def main():
    app = QApplication(sys.argv)
    win = MainWindow()
    win.show()
    return app.exec()

if __name__ == '__main__':
    main()