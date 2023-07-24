import fitz
import logging
import re
import json

from paddleocr import PaddleOCR
import argparse
from PIL import Image
import fitz
from scipy.optimize import minimize
import tempfile
import matplotlib.pyplot as plt


def page_column_split_y0(arr):
    def objective(x, arr):
        return sum(abs(x - num) for num in arr)
    result = minimize(objective, x0=0, args=(arr,), method='BFGS')
    return result.x[0]


class Chunk:
    page_header = ""
    page_footer = ""
    text = ""
    titles = {}
    page_num = 0

    def __init__(self, text, page_num):
        self.text = text
        self.page_num = page_num


class TextBlock:
    rect: fitz.Rect = None
    text = ""
    confidence = 1
    page_index = 0
    page_rect: fitz.Rect = None

    def __init__(self, rect, text, page_index, page_rect):
        self.rect = rect
        self.text = text
        self.page_index = page_index
        self.page_rect = page_rect


class PDFSplitter:
    text_blocks = None
    ocr_engine = None
    ocr: bool = False
    bucket_num = 100  # title分级分桶数
    header_range = 20  # 距离高度占比1/20
    footer_range = 20  # 距离高度占比1/20
    block_type_code = {
        0: "text",
        1: "image",
    }

    path = None

    def __init__(self, path):
        self.path = path

    def is_header(self, page_rect, block_rect):

        return (block_rect.y0-page_rect.y0) < ((page_rect.y1-page_rect.y0)/self.header_range)

    def is_footer(self, page_rect, block_rect):

        return (page_rect.y1-block_rect.y1) < ((page_rect.y1-page_rect.y0)/self.footer_range)

    def get_text_blocks(self) -> list[TextBlock]:
        if self.ocr:
            return self.__text_blocks__orc()
        return self.__text_blocks()

    def __text_blocks__orc(self) -> list[TextBlock]:
        text_block_list = []
        doc = fitz.open(path)
        for page_index, page in enumerate(doc):
            print(f"text block number ocr page:{page_index}")
            lines = []
            # page to image
            pix = page.get_pixmap(dpi=500)
            tmp = tempfile.NamedTemporaryFile(suffix='.png', prefix='tmp')
            pix.save(tmp.name)
            img_path = tmp.name
            page_rect = None
            with Image.open(img_path) as img:
                w, h = img.size
                page_rect = fitz.Rect(0, 0, w, h)
                # print(f"page {page_index} width:{w}, height:{h}")

            # ocr
            result = self.ocr_engine.ocr(img_path, cls=True)

            # get text blocks
            x0_list = []
            x0_min = page_rect.x0
            x0_max = page_rect.x1
            for res in result:
                for line_data in res:
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
                    if confidence < 0.5:
                        continue

                    # only take center part to guess if double column page
                    if y0 > page_rect.y1/6 and y1 < page_rect.y1*(6-1)/6:
                        x0_list.append(x0)

                    if x0 < x0_min:
                        x0_min = x0
                    if x0 > x0_max:
                        x0_max = x0

                    line_rect = fitz.Rect(x0, y0, x1, y1)
                    line = TextBlock(line_rect, text, page_index, page_rect)
                    lines.append(line)

            # check column
            two_column = False  # one column if Flase
            column_splitt_x0 = page_column_split_y0(x0_list)
            if (column_splitt_x0 - x0_min) > ((x0_max-x0_min)/10):
                two_column = True
                # print("two column split x0 with", column_splitt_x0)

            # sort lines
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

            text_block_list.extend(sorted_lines)

        return text_block_list

    def __text_blocks(self) -> list[TextBlock]:
        doc_path = self.path
        text_block_list = []
        doc_pdf = fitz.open(doc_path)
        for page_index, page in enumerate(doc_pdf):
            blocks = page.get_text("blocks", sort=False)
            page_rect = page.bound()
            for block_index, block in enumerate(blocks):
                if len(block) < 7:
                    logging.error(
                        f"block format error {block} block index{block_index} page index {page_index}")
                    continue
                x0 = block[0]
                y0 = block[1]
                x1 = block[2]
                y1 = block[3]
                if x1 < x0 or y1 < y0:
                    continue
                block_type = self.block_type_code.get(block[6], "else")
                if block_type == 'text':
                    text = block[4]
                    zh_word_num = self.__class__.count_words(text)
                    if zh_word_num == 0:
                        continue
                    text_block = TextBlock(
                        fitz.Rect(x0, y0, x1, y1), text, page_index, page_rect)
                    text_block_list.append(text_block)
        return text_block_list

    @classmethod
    def count_words(cls, text):
        pattern = r'[\u4e00-\u9fa5]|\w+'
        words = re.findall(pattern, text)
        return len(words)

    def lines_height(self) -> list[int]:
        line_height_list = []
        total_height = 0
        lines = 0
        if self.text_blocks == None:
            self.text_blocks = self.get_text_blocks()
        for block in self.text_blocks:
            block_lines = len(block.text.split('\n', -1))-1
            if block_lines < 1:
                block_lines = 1
            lines += block_lines
            height = (block.rect.y1 - block.rect.y0)/block_lines
            line_height = height
            # line_height = height*height
            total_height += height
            line_height_list.append(line_height)
        return line_height_list

    def plot_height_sqr(self):
        title_splitter = self.title_level_splitter()
        print(f"title level split by {title_splitter}")
        word_size_list = self.lines_height()
        num_bins = self.bucket_num
        min_value = min(word_size_list)
        max_value = max(word_size_list)

        plt.hist(word_size_list, bins=num_bins, range=(
            min_value, max_value), edgecolor='black')
        plt.title('Histogram')
        plt.xlabel('Value')
        plt.ylabel('Frequency')
        plt.savefig('./plot.png')

    def title_level_splitter(self):
        arr = self.lines_height()
        bucket_num = self.bucket_num
        # get bucket
        arr.sort()
        min_value = arr[0]
        max_value = arr[-1]
        bucket_size = (max_value - min_value) / bucket_num
        buckets = {}
        for i in range(bucket_num):
            buckets[i] = []

        for num in arr:
            bucket_index = int((num - min_value) // bucket_size)
            if bucket_index == bucket_num:
                bucket_index = bucket_num-1
            buckets[bucket_index].append(num)

        # get split width=3, split[(min,max)]
        level_split = []
        total_cnt = len(arr)
        peak_index = None
        max_cnt = 0
        for i, bucket in buckets.items():
            if len(bucket) > max_cnt:
                peak_index = i
                max_cnt = len(bucket)

        last_cnt = max_cnt
        min_split = None
        max_split = None

        min_split = min_value + (peak_index-1)*bucket_size
        max_split = min_split + bucket_size*3
        if min_split < min_value:
            min_split = min_value
        if max_split > max_value:
            max_split = max_value

        level_split.append((min_split, max_split))

        up = False
        for i, bucket in buckets.items():
            last_cnt_cp = last_cnt
            last_cnt = len(bucket)
            if i <= peak_index:
                continue
            if len(bucket) <= last_cnt_cp:
                up_cp = up
                up = False
                if up_cp:
                    peak_index = i-1
                    if len(buckets[peak_index]) < (total_cnt/self.bucket_num/5):
                        continue
                    min_split = min_value + (peak_index-1)*bucket_size
                    max_split = min_split + bucket_size*3
                    if min_split < min_value:
                        min_split = min_value
                    if max_split > max_value:
                        max_split = max_value
                    (last_min, last_max) = level_split[-1]
                    if min_split < last_max:
                        level_split[-1] = (last_min, max_split)
                    else:
                        level_split.append((min_split, max_split))
            else:
                up = True

        return level_split

    # def split(self) -> list[Chunk]:
    #     if self.ocr:
    #         return self.__split_orc()
    #     return self.__split()

    # def __split_orc(self) -> list[Chunk]:
    #     pass

    def split(self) -> list[Chunk]:
        title_splitter = self.title_level_splitter()
        print(f"title level split by {title_splitter}")
        doc_pdf = fitz.open(path)

        base_text = ""
        titles = {}
        for level, _ in enumerate(title_splitter):
            titles[level] = ""
        chunks = []
        page_header = {}
        page_footer = {}
        last_block_level = 0
        if self.text_blocks == None:
            self.text_blocks = self.get_text_blocks()
        for block in self.text_blocks:
            page_rect = block.page_rect
            # header footer
            if self.is_header(page_rect, block.rect):
                page_header[block.page_index] = block.text
                # new chunk if page header change
                # if page_header.get(page_index-1, "") != text and base_text != "":
                #     chunk = Chunk(base_text, page_index)
                #     chunk.titles = titles.copy()
                #     chunks.append(chunk)
                #     # clear text and title
                #     last_block_level = 0
                #     base_text = ""
                #     titles = {}
                continue
            if self.is_footer(page_rect, block.rect):
                page_footer[block.page_index] = block.text
                continue

            # get height
            block_lines = len(block.text.split('\n', -1))-1
            if block_lines < 1:
                block_lines = 1
            height = (block.rect.y1 - block.rect.y0)/block_lines
            # height = height*height

            # check title
            block_level = 0
            for level, (min, max) in enumerate(title_splitter):
                if height > min and height < max:
                    block_level = level
                    break

            # split by level 1
            if block_level == 0:
                base_text += block.text
            else:
                # new chunk
                if last_block_level == 0:
                    chunk = Chunk(base_text, block.page_index)
                    chunk.titles = titles.copy()
                    chunks.append(chunk)
                    base_text = block.text

                # update title
                for level, _ in titles.items():
                    if level < block_level:
                        titles[level] = ""
                titles[block_level] = block.text

            last_block_level = block_level

        if base_text != "":
            chunk = Chunk(base_text, len(doc_pdf)-1)
            chunk.titles = titles.copy()
            chunks.append(chunk)

        for chunk in chunks:
            chunk.page_header = page_header.get(chunk.page_num, "")
            chunk.page_footer = page_footer.get(chunk.page_num, "")

        return chunks


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--path", type=str)
    parser.add_argument("--output", type=str)
    parser.add_argument("--plot", type=bool, default=False)
    parser.add_argument("--ocr", type=bool, default=False)
    parser.add_argument("--bucket", type=int, default=100)
    args = parser.parse_args()
    path = args.path
    output = args.output
    splitter = PDFSplitter(path)
    splitter.bucket_num = args.bucket
    splitter.ocr = args.ocr
    if splitter.ocr:
        splitter.ocr_engine = PaddleOCR(use_angle_cls=True, lang="ch")
    if args.plot:
        splitter.plot_height_sqr()

    else:
        chunks = splitter.split()
        chunks_json = json.dumps(chunks, ensure_ascii=False,
                                 default=lambda obj: obj.__dict__)

        with open(output, 'w+') as file:
            file.write(chunks_json)
