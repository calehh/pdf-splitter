from PIL import Image
import fitz
import argparse
import os
import cv2

parser = argparse.ArgumentParser()
parser.add_argument("--path", type=str)
parser.add_argument("--output", type=str)
args = parser.parse_args()
path = args.path
output = args.output
print(path)
print(output)

if not os.path.exists(output):
    os.makedirs(output)
    print(f"make new dir {output}")

doc = fitz.open(path)

for page_index in range(len(doc)):
    page = doc[page_index]
    pix = page.get_pixmap(dpi=500)
    page_image_path = f"{output}/page_{page_index}.png"
    pix.save(page_image_path)
    


###from paddleocr utils
# imgs = []
# with fitz.open(path) as pdf:
#     for pg in range(0, len(pdf)):
#         page = pdf[pg]
#         mat = fitz.Matrix(2, 2)
#         pm = page.get_pixmap(matrix=mat, alpha=False)

#         # if width or height > 2000 pixels, don't enlarge the image
#         if pm.width > 2000 or pm.height > 2000:
#             pm = page.get_pixmap(matrix=fitz.Matrix(1, 1), alpha=False)

#         img = Image.frombytes("RGB", [pm.width, pm.height], pm.samples)
#         img = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)
#         imgs.append(img)
