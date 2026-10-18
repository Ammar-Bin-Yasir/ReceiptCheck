"""Create a synthetic, non-personal receipt for the reproducible demo."""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

root = Path(__file__).resolve().parents[1]
target = root / "examples"
target.mkdir(exist_ok=True)
font_path = "/usr/share/fonts/dejavu-sans-mono-fonts/DejaVuSansMono.ttf"
if not Path(font_path).exists():
    font_path = "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf"
font = ImageFont.truetype(font_path, 28) if Path(font_path).exists() else ImageFont.load_default(size=28)
image = Image.new("RGB", (920, 1020), "#fffefa")
draw = ImageDraw.Draw(image)
lines = [
    "         LAHORE OFFICE MART", "        SAMPLE RECEIPT / DEMO", "",
    "Date: 2026-10-18", "Currency: PKR", "Receipt: DEMO-001", "",
    "Item             Qty   Price  Amount", "------------------------------------",
    "Notebook           2  250.00  500.00", "Blue pen           1  100.00  100.00",
    "------------------------------------", "Subtotal                      600.00",
    "Tax                            60.00", "Discount                        0.00",
    "TOTAL (PKR)                   660.00", "", "           Thank you!", "",
    "Synthetic example, not a real sale.",
]
for index, line in enumerate(lines):
    draw.text((55, 50 + index * 44), line, font=font, fill="#151515")
image.save(target / "sample-receipt.png")
print(target / "sample-receipt.png")
