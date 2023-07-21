from PIL import Image
import fitz
from pdf2image import convert_from_path
import argparse
import os

parser = argparse.ArgumentParser()
parser.add_argument("--path", type=str)
parser.add_argument("--output", type=str)
args = parser.parse_args()
path = args.path
output = args.output
print(path)

doc = fitz.open(path)

if not os.path.exists(output):
    os.makedirs(output)
    print(f"make new dir {output}")


def save_pdf_as_images(pdf_path, output_dir, page_index, image_format='png',):
    page_index += 1
    images = convert_from_path(
        pdf_path, first_page=page_index, last_page=page_index)

    for i, image in enumerate(images):
        image_path = f"{output_dir}/page_{page_index}.{image_format}"
        image.save(image_path, image_format)


def crop_image(image, output_path, page_rect, image_rect):
    width, height = image.size
    width_scale = width/page_rect.width
    height_scale = height/page_rect.height
    x_min = (image_rect.x0-page_rect.x0) * width_scale
    x_max = (image_rect.x1-page_rect.x0) * width_scale
    y_min = (image_rect.y0-page_rect.y0) * height_scale
    y_max = (image_rect.y1-page_rect.y0) * height_scale
    cropped_image = image.crop((x_min, y_min, x_max, y_max))
    cropped_image.save(output_path)


for page_index in range(len(doc)):
    page = doc[page_index]
    blocks = page.get_text("blocks", sort=False)
    page_rect = page.bound()
    pdf2image_index = page_index + 1
    images = convert_from_path(
        path, first_page=pdf2image_index, last_page=pdf2image_index)
    page_image = images[0]

    # pix = page.get_pixmap(dpi=500)
    # page_image_path = f"{output}/model3_page_{page_index}.png"
    # pix.save(page_image_path)

    for block_index, block in enumerate(blocks):
        if block[6] != 10:  # block type
            x0 = block[0]
            y0 = block[1]
            x1 = block[2]
            y1 = block[3]
            rect = fitz.Rect(x0, y0, x1, y1)
            if x0 < page_rect.x0 or x1 > page_rect.x1 or y0 < page_rect.y0 or y1 > page_rect.y1:
                print(f"block error: {block}")
                continue
            print(f"block: {block}")
            output_path = f"{output}/page_{page_index}_block_{block_index}.png"
            crop_image(page_image, output_path, page_rect, rect)
