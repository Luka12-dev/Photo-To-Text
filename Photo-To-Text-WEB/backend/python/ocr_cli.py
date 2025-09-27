#!/usr/bin/env python
# ocr_cli.py - simple CLI that prints OCR or AI description to stdout
# usage: python ocr_cli.py /path/to/image.png --ai

import sys
import os
from PIL import Image
import pytesseract

# default tesseract path for Windows users - update if necessary
if os.name == 'nt':
    pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

# parse args
args = sys.argv[1:]
if not args:
    print("no input", file=sys.stderr)
    sys.exit(2)

image_path = args[0]
use_ai = '--ai' in args

# OCR attempt
try:
    img = Image.open(image_path)
    text = pytesseract.image_to_string(img, lang='eng').strip()
except Exception as e:
    print("ocr error: " + str(e), file=sys.stderr)
    sys.exit(3)

if text:
    # OCR succeeded - print it
    print(text)
    sys.exit(0)

# OCR empty - optional AI fallback
if use_ai:
    # this block uses BLIP if available - otherwise returns empty
    try:
        from transformers import BlipProcessor, BlipForConditionalGeneration
        import torch
        proc = BlipProcessor.from_pretrained("Salesforce/blip-image-captioning-base", use_fast=True)
        model = BlipForConditionalGeneration.from_pretrained("Salesforce/blip-image-captioning-base")
        device = "cuda" if torch.cuda.is_available() else "cpu"
        model.to(device)
        inputs = proc(img.convert("RGB"), return_tensors="pt").to(device)
        out = model.generate(**inputs, max_length=120, num_beams=3)
        desc = proc.decode(out[0], skip_special_tokens=True)
        print(desc)
        sys.exit(0)
    except Exception as e:
        print("ai fallback error: " + str(e), file=sys.stderr)
        sys.exit(4)

# no result
print("", end="")
sys.exit(0)