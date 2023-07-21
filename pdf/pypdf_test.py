from pypdf import PdfReader
pdf_filepath = "/Users/houmingyu/Downloads/model3_instruction.pdf"
reader = PdfReader(pdf_filepath)
number_of_pages = len(reader.pages)
page = reader.pages[0]
image = page.images[0]

with open("./image", "wb") as img_file:
    img_file.write(image.data)
text = page.extract_text()
print(text)