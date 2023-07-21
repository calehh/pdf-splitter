import camelot

path = "/Users/houmingyu/Documents/chatgpt/Chinese-LLaMA-Alpaca/scripts/pdf/model3_instruction.pdf"

tablelist = camelot.read_pdf(path, pages='37,38,39')

print(type(tablelist[0]))

print(tablelist[0])
