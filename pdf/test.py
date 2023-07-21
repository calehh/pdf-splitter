import re

def count_words(text):
    pattern = r'[\u4e00-\u9fa5]|\w+'
    words = re.findall(pattern, text)
    return len(words)

# 测试
text = "Hello 你好，这是一段包含 English 英文的文本。"
word_count = count_words(text)
print("词数:", len(text))
