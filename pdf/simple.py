import fitz
import logging
from sklearn.cluster import KMeans, DBSCAN
import numpy as np
import re
import json
import matplotlib.pyplot as plt
import os

path = '/Users/houmingyu/Documents/chatgpt/pdf-indexer/pdf/ec6.pdf'


block_type_code = {
    0: "text",
    1: "image",
}


def title_height_split(arr, bucket_num):
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
                if len(buckets[peak_index]) < (total_cnt/200):
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


def count_zh_words(text):
    pattern = r'[\u4e00-\u9fa5]|\w+'
    words = re.findall(pattern, text)
    return len(words)


def count_words(text):
    return len(text)
    # pattern = r'[\u4e00-\u9fa5]|\w+'
    # words = re.findall(pattern, text)
    # return len(words)


# def pdf_word_size(doc_path: str) -> list[int]:
#     char_size_list = []
#     doc_pdf = fitz.open(doc_path)
#     total_size = 0
#     total_char_num = 0
#     for page_index, page in enumerate(doc_pdf):
#         blocks = page.get_text("blocks", sort=False)
#         for block_index, block in enumerate(blocks):
#             if len(block) < 7:
#                 logging.error(
#                     f"block format error {block} block index{block_index} page index {page_index}")
#                 continue
#             x0 = block[0]
#             y0 = block[1]
#             x1 = block[2]
#             y1 = block[3]
#             if x1 < x0 or y1 < y0:
#                 continue
#             block_type = block_type_code.get(block[6], "else")
#             if block_type == 'text':
#                 text = block[4]
#                 # text = text.encode("utf-8").decode("unicode_escape")
#                 words_num = count_words(text)
#                 if words_num == 0:
#                     continue
#                 total_char_num += words_num

#                 block_size = (x1-x0) * (y1-y0)
#                 total_size += block_size

#                 average_char_size = block_size/words_num

#                 size_list = [average_char_size] * words_num
#                 char_size_list.extend(size_list)
#     average_size = total_size/total_char_num
#     print(f"average size:{average_size}")
#     return char_size_list


def pdf_average_height(doc_path: str) -> list[int]:
    line_height_list = []
    doc_pdf = fitz.open(doc_path)
    total_height = 0
    lines = 0
    for page_index, page in enumerate(doc_pdf):
        blocks = page.get_text("blocks", sort=False)
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
            block_type = block_type_code.get(block[6], "else")
            if block_type == 'text':
                text = block[4]
                zh_word_num = count_zh_words(text)
                if zh_word_num == 0:
                    continue
                block_lines = len(text.split('\n', -1))-1
                if block_lines < 1:
                    block_lines = 1
                lines += block_lines
                height = (y1 - y0)/block_lines
                line_height = height*height
                total_height += height
                line_height_list.append(line_height)
    average_height = total_height/lines
    print(f"average height:{average_height}")
    return line_height_list


word_size_list = pdf_average_height(path)
print("total lines:", len(word_size_list))

title_splitter = title_height_split(word_size_list, 200)

for i, e in enumerate(title_splitter):
    print(f"level {i}:{e}")


# 画直方图
num_bins = 200
min_value = min(word_size_list)
max_value = max(word_size_list)
bin_width = (max_value - min_value) / num_bins

plt.hist(word_size_list, bins=num_bins, range=(
    min_value, max_value), edgecolor='black')
plt.title('Histogram')
plt.xlabel('Value')
plt.ylabel('Frequency')
plt.show()

# KMEANS
# cluster_num = 5

# data = np.array(word_size_list)
# X = data.reshape(-1, 1)
# km = KMeans(n_clusters=cluster_num).fit(X)

# centers = km.cluster_centers_.flatten()
# center_label = {}
# for lable, center in enumerate(centers):
#     center_label[lable] = center

# print(center_label)

# i = 0
# label_format = {}
# for k, v in dict(sorted(center_label.items(), key=lambda x: x[1])).items():
#     label_format[k] = i
#     i += 1

# print(label_format)

# label_list = {}
# label_cnt = {}
# for i in range(cluster_num):
#     label_cnt[i] = 0

# for i in range(len(word_size_list)):
#     size = word_size_list[i]
#     label = label_format[km.labels_[i]]
#     label_cnt[label] += 1
#     label_list[size] = label

# print(label_cnt)


# def is_header(page_rect, block_rect):

#     return (block_rect.y0-page_rect.y0) < ((page_rect.y1-page_rect.y0)/20)


# def is_footer(page_rect, block_rect):

#     return (page_rect.y1-block_rect.y1) < ((page_rect.y1-page_rect.y0)/20)


# class Chunk:
#     page_header = ""
#     page_footer = ""
#     text = ""
#     titles = {}
#     page_num = 0

#     def __init__(self, text, page_num):
#         self.text = text
#         self.page_num = page_num


# # 处理文档
# doc_pdf = fitz.open(path)
# base_text = ""

# titles = {}
# for level, _ in enumerate(title_splitter):
#     titles[level] = ""

# chunks = []
# page_header = {}
# page_footer = {}
# for page_index, page in enumerate(doc_pdf):
#     page_rect = page.bound()
#     blocks = page.get_text("blocks", sort=False)
#     last_block_level = 0
#     for block_index, block in enumerate(blocks):
#         if len(block) < 7:
#             logging.error(
#                 f"block format error {block} block index{block_index} page index {page_index}")
#             continue
#         x0 = block[0]
#         y0 = block[1]
#         x1 = block[2]
#         y1 = block[3]
#         block_rect = fitz.Rect(x0, y0, x1, y1)
#         if x1 < x0 or y1 < y0:
#             continue
#         block_type = block_type_code.get(block[6], "else")
#         if block_type == 'text':
#             text = block[4]
#             zh_word_num = count_zh_words(text)
#             if zh_word_num == 0:
#                 continue
#             # header footer
#             if is_header(page_rect, block_rect):
#                 page_header[page_index] = text
#                 # new chunk if page header change
#                 # if page_header.get(page_index-1, "") != text and base_text != "":
#                 #     chunk = Chunk(base_text, page_index)
#                 #     chunk.titles = titles.copy()
#                 #     chunks.append(chunk)
#                 #     # clear text and title
#                 #     last_block_level = 0
#                 #     base_text = ""
#                 #     titles = {}
#                 continue
#             if is_footer(page_rect, block_rect):
#                 page_footer[page_index] = text
#                 continue

#             # get height
#             block_lines = len(text.split('\n', -1))-1
#             if block_lines < 1:
#                 block_lines = 1
#             height = (y1 - y0)/block_lines
#             height = height*height

#             # check title
#             block_level = 0
#             for level, (min, max) in enumerate(title_splitter):
#                 if height > min and height < max:
#                     block_level = level
#                     break

#             # split by level 1
#             if block_level == 0:
#                 base_text += text
#             else:
#                 # new chunk
#                 if last_block_level == 0:
#                     chunk = Chunk(base_text, page_index)
#                     chunk.titles = titles.copy()
#                     chunks.append(chunk)
#                     base_text = text

#                 # update title
#                 for level, _ in titles.items():
#                     if level < block_level:
#                         titles[level] = ""
#                 titles[block_level] = text

#             last_block_level = block_level

# if base_text != "":
#     chunk = Chunk(base_text, len(doc_pdf)-1)
#     chunk.titles = titles.copy()
#     chunks.append(chunk)

# for chunk in chunks:
#     chunk.page_header = page_header.get(chunk.page_num, "")
#     chunk.page_footer = page_footer.get(chunk.page_num, "")

# json_data = json.dumps(chunks, ensure_ascii=False,
#                        default=lambda obj: obj.__dict__)
# with open("./chunks.json", 'w+') as file:
#     file.write(json_data)
