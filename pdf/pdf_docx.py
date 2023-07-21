from pdf2docx import parse
import argparse
parser = argparse.ArgumentParser()
parser.add_argument("--path", type=str)
parser.add_argument("--output", type=str)
args = parser.parse_args()

pdf_file = args.path
docx_file = args.output

# convert pdf to docx
parse(pdf_file, docx_file)
