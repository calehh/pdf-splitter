import os

from paddleocr import PPStructure, save_structure_res, PaddleOCR
from paddleocr.ppstructure.recovery.recovery_to_doc import sorted_layout_boxes, convert_info_docx
import argparse
from PIL import Image
import fitz
from scipy.optimize import minimize
import tempfile


def page_column_split_y0(arr):
    def objective(x, arr):
        return sum(abs(x - num) for num in arr)
    result = minimize(objective, x0=0, args=(arr,), method='BFGS')
    return result.x[0]


parser = argparse.ArgumentParser()
parser.add_argument("--path", type=str)
parser.add_argument("--output", type=str)
parser.add_argument("--model", type=str)
args = parser.parse_args()

model_path = args.model
save_folder = args.output
path = args.path
page_index = 10

doc = fitz.open(path)

page = doc[page_index]
pix = page.get_pixmap(dpi=500)

tmp = tempfile.NamedTemporaryFile(suffix='.png', prefix='tmp')
pix.save(tmp.name)
img_path = tmp.name

page_rect = None
with Image.open(img_path) as img:
    w, h = img.size
    page_rect = fitz.Rect(0, 0, w, h)
    print(f"page width:{w}, height:{h}")


class Line:
    rect: fitz.Rect = None
    text = ""
    confidence = 1

    def __init__(self, rect, text, confidence):
        self.rect = rect
        self.text = text
        self.confidence = confidence


# ocr
ocr = PaddleOCR(use_angle_cls=True, lang="ch")
result = ocr.ocr(img_path, cls=True)

lines = []
x0_list = []
x0_min = page_rect.x0
x0_max = page_rect.x1
for res in result:
    for line_data in res:
        print(line_data, '\n')
        if len(line_data) != 2:
            print(f"line result structure error 1 {line_data}",)
            continue
        if len(line_data[0]) != 4:
            print(f"line result structure error 2 {line_data}",)
            continue
        if len(line_data[0][0]) != 2 or len(line_data[0][3]) != 2:
            print(f"line result structure error 3 {line_data}",)
            continue

        x0 = line_data[0][0][0]
        x1 = line_data[0][3][0]
        y0 = line_data[0][0][1]
        y1 = line_data[0][3][1]
        (text, confidence) = line_data[1]

        # only take center part to guess if double column page
        if y0 > page_rect.y1/6 and y1 < page_rect.y1*(6-1)/6:
            x0_list.append(x0)

        if x0 < x0_min:
            x0_min = x0
        if x0 > x0_max:
            x0_max = x0

        line_rect = fitz.Rect(x0, y0, x1, y1)
        line = Line(line_rect, text, confidence)
        lines.append(line)

print(x0_list)
two_column = False  # one column if Flase
column_splitt_x0 = page_column_split_y0(x0_list)
if (column_splitt_x0 - x0_min) > ((x0_max-x0_min)/10):
    two_column = True
    print("two column split x0 with", column_splitt_x0)

sorted_lines = []
if not two_column:
    sorted_lines = sorted(lines, key=lambda line: line.rect.y0)

else:
    left_column = []
    right_column = []
    for line in lines:
        if line.rect.x0 > column_splitt_x0:
            right_column.append(line)
        else:
            left_column.append(line)
    left_column.sort(key=lambda line: line.rect.y0)
    right_column.sort(key=lambda line: line.rect.y0)
    sorted_lines.extend(left_column)
    sorted_lines.extend(right_column)

for l in sorted_lines:
    print(l.text, "\n")

# table_engine = PPStructure(
#     structure_version="PP-StructureV2", lang='ch', table=False, ocr=False)
# img = cv2.imread(img_path)
# result = table_engine(img)
# save_structure_res(result, save_folder,
#                    os.path.basename(img_path).split('.')[0])


# 版面恢复
# table_engine = PPStructure(
#     recovery=True, use_pdf2docx_api=True, image_dir=img_path)
# # img = cv2.imread(img_path)
# result = table_engine()
# save_structure_res(result, save_folder,
#                    os.path.basename(img_path).split('.')[0])

# for line in result:
#     line.pop('img')
#     print(line)

# h, w, _ = img.shape
# res = sorted_layout_boxes(result, w)
# convert_info_docx(img, res, save_folder,
#                   os.path.basename(img_path).split('.')[0])


# 版面分析
# table_engine = PPStructure(table=False, ocr=True,
#                            show_log=True, layout_model_dir=model_path)


# img = cv2.imread(img_path)
# result = table_engine(img)
# save_structure_res(result, save_folder,
#                    os.path.basename(img_path).split('.')[0])

# for line in result:
#     line.pop('img')
#     print(line)
