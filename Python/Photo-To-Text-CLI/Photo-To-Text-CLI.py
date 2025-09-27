import pytesseract
from PIL import Image
import time
import sys
import os
import warnings
from colorama import Fore, Style, init

# Disable annoying warnings
os.environ["HF_HUB_DISABLE_SYMLINKS_WARNING"] = "1"
os.environ["TRANSFORMERS_NO_ADVISORY_WARNINGS"] = "1"
os.environ["HF_HUB_DISABLE_PROGRESS_BARS"] = "1"
warnings.filterwarnings("ignore")

# Initialize colors
init(autoreset=True)

# Path to Tesseract (update if needed)
pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

# Flags
USE_AI = False
blip_processor, blip_model = None, None
MODEL_DIR = "blip_model"

try:
    from transformers import BlipProcessor, BlipForConditionalGeneration, logging
    import torch

    logging.set_verbosity_error()  # block HF spam
    USE_AI = True
except ImportError:
    pass

# CLI Effects
def animate_text(text, color=Fore.CYAN, delay=0.03):
    for char in text:
        sys.stdout.write(color + char + Style.RESET_ALL)
        sys.stdout.flush()
        time.sleep(delay)
    print()

def fake_loader(msg="AI loading", steps=10, delay=0.3):
    for i in range(steps + 1):
        percent = int((i / steps) * 100)
        sys.stdout.write(f"\r{Fore.MAGENTA}{msg}: {percent}%{Style.RESET_ALL}")
        sys.stdout.flush()
        time.sleep(delay)
    print()

# AI Loader
def init_blip():
    global blip_processor, blip_model

    if blip_model is not None and blip_processor is not None:
        return  # already loaded

    animate_text("⚡ Initializing AI model...", Fore.MAGENTA, 0.02)

    # If cached model exists, ask user
    if os.path.exists(MODEL_DIR):
        choice = input(Fore.YELLOW + "⚠️ Cached model found. Reload? (y/N): " + Style.RESET_ALL).strip().lower()
        if choice != "y":
            fake_loader("AI loading", steps=5, delay=0.2)
            blip_processor = BlipProcessor.from_pretrained(MODEL_DIR)
            blip_model = BlipForConditionalGeneration.from_pretrained(MODEL_DIR)
            return
        else:
            import shutil
            shutil.rmtree(MODEL_DIR)

    # Fake bar while downloading
    fake_loader("AI downloading", steps=20, delay=0.15)

    # Real download
    blip_processor = BlipProcessor.from_pretrained("Salesforce/blip-image-captioning-base")
    blip_model = BlipForConditionalGeneration.from_pretrained("Salesforce/blip-image-captioning-base")

    # Cache locally
    blip_processor.save_pretrained(MODEL_DIR)
    blip_model.save_pretrained(MODEL_DIR)

def describe_image(img_path):
    if not USE_AI:
        return "[!] No text detected and AI is not available."

    init_blip()
    image = Image.open(img_path).convert("RGB")

    inputs = blip_processor(image, return_tensors="pt")
    out = blip_model.generate(**inputs, max_length=100, num_beams=3, early_stopping=True)
    return blip_processor.decode(out[0], skip_special_tokens=True)

# Main Program
def main():
    os.system("cls" if os.name == "nt" else "clear")

    # Intro banner
    print(Fore.MAGENTA + "═" * 60 + Style.RESET_ALL)
    animate_text("👾  PHOTO → TEXT / CODE CONVERTER  👾", Fore.CYAN, 0.02)
    print(Fore.MAGENTA + "═" * 60 + Style.RESET_ALL)

    # Ask for file
    img_path = input(Fore.YELLOW + "📂 Enter image filename (e.g., image.png): " + Style.RESET_ALL).strip()

    if not os.path.exists(img_path):
        print(Fore.RED + "❌ File does not exist!" + Style.RESET_ALL)
        return

    # OCR
    animate_text("🔎 Scanning with OCR...", Fore.BLUE, 0.03)
    img = Image.open(img_path)
    text = pytesseract.image_to_string(img, lang="eng").strip()

    if text:
        animate_text("✅ Text detected:", Fore.GREEN, 0.03)
        print(Fore.CYAN + "-" * 50 + Style.RESET_ALL)
        print(Fore.WHITE + text + Style.RESET_ALL)
        print(Fore.CYAN + "-" * 50 + Style.RESET_ALL)

        with open("output.txt", "w", encoding="utf-8") as f:
            f.write(text)

        animate_text("💾 Saved to output.txt", Fore.GREEN, 0.02)
    else:
        animate_text("⚠️ No text found! Switching to AI...", Fore.YELLOW, 0.03)
        if USE_AI:
            desc = describe_image(img_path)
            animate_text("🤖 AI description:", Fore.MAGENTA, 0.02)
            print(Fore.CYAN + "-" * 50 + Style.RESET_ALL)
            print(Fore.WHITE + desc + Style.RESET_ALL)
            print(Fore.CYAN + "-" * 50 + Style.RESET_ALL)

            with open("output.txt", "w", encoding="utf-8") as f:
                f.write(desc)

            animate_text("💾 Saved to output.txt", Fore.GREEN, 0.02)
        else:
            print(Fore.RED + "❌ OCR failed and AI not installed." + Style.RESET_ALL)


if __name__ == "__main__":
    main()
