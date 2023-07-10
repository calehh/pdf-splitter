# -*- coding:utf-8 -*-
from flask_restful import reqparse
from . import api
from flask_restful import Resource, marshal_with, fields, marshal
import fitz
from models.block import Document, Page, Block, update_object_flush
import os
from .error import FileNotExistError
from extensions.ext_database import db
import logging
from extensions.ext_storage import storage
from pdf2image import convert_from_path
import tempfile
from sqlalchemy.exc import IntegrityError


def crop_rect(image, file, page_rect: fitz.Rect, image_rect: fitz.Rect):
    width, height = image.size
    width_scale = width/page_rect.width
    height_scale = height/page_rect.height
    x_min = (image_rect.x0-page_rect.x0) * width_scale
    x_max = (image_rect.x1-page_rect.x0) * width_scale
    y_min = (image_rect.y0-page_rect.y0) * height_scale
    y_max = (image_rect.y1-page_rect.y0) * height_scale
    cropped_image = image.crop((x_min, y_min, x_max, y_max))
    cropped_image.save(file)


class Check(Resource):
    def post(self):
        parser = reqparse.RequestParser()
        parser.add_argument('input', type=str, location='json')
        args = parser.parse_args()
        resp = f"{args['input']} success"
        return {'result': resp}, 200

    def get(self):
        return {'result': 'success'}, 200


block_type_code = {
    0: "text",
    1: "image",
}


class AddDoc(Resource):
    def post(self):
        parser = reqparse.RequestParser()
        parser.add_argument('path', type=str, location='json')
        args = parser.parse_args()
        doc_path = args['path']
        if not os.path.exists(doc_path):
            raise FileNotExistError()
        if not os.path.isfile(doc_path):
            raise FileNotExistError()

        doc_pdf = fitz.open(args['path'])

        page_num = len(doc_pdf)
        document = Document(
            name=os.path.basename(doc_path),
            path=doc_path,
            page_cnt=page_num,
        )
        try:
            db.session.add(document)
            db.session.flush()
        except InterruptedError:
            db.session.rollback()
            document_db = db.session.query(Document).filter(
                Document.path == doc_path).first()
            update_object_flush(document_db, **document.__dict__)
        if document_db is not None:
            document = document_db
        logging.info(f"add document {document.__dict__}")

        for page_index, page in enumerate(doc_pdf):
            blocks = page.get_text("blocks", sort=False)
            block_cnt = len(blocks)

            page_rect = page.bound()

            page_row = Page(
                doc_id=document.id,
                page_num=page_index,
                block_cnt=block_cnt,
                x0=page_rect.x0,
                x1=page_rect.x1,
                y0=page_rect.y0,
                y1=page_rect.y1,
            )
            try:
                db.session.add(page_row)
                db.session.flush()
            except IndentationError:
                db.session.rollback()
                page_db = db.session.query(Page).filter(
                    Page.doc_id == document.id, Page.page_num == page_index).first()
                update_object_flush(page_db, **page_row.__dict__)
            if page_db is not None:
                page_row = page_db
            logging.info(f"page {page_row.__dict__}")

            # get page image
            pdf2image_index = page_index + 1
            images = convert_from_path(
                doc_path, first_page=pdf2image_index, last_page=pdf2image_index)
            page_image = images[0]
            for block_num, block_pdf in enumerate(blocks):
                if len(block_pdf) < 7:
                    logging.error(f"block format error {block_pdf}")
                    continue
                typee = block_type_code.get(block_pdf[6], "else")
                if typee == "text":
                    text = block_pdf[4]
                block = Block(
                    x0=block_pdf[0],
                    y0=block_pdf[1],
                    x1=block_pdf[2],
                    y1=block_pdf[3],
                    block_num=block_num,
                    page_id=page_row.id,
                    doc_id=document.id,
                    typee=typee,
                    text=text,
                )
                try:
                    db.session.add(block)
                    db.session.flush()
                except IntegrityError:
                    db.session.rollback()
                    block_db = db.session.query(Block).filter(
                        Block.doc_id == document.id, Block.page_id == page_row.id, Block.block_num == block_num).first()
                    update_object_flush(block_db, **block.__dict__)
                if block_db is not None:
                    block = block_db
                logging.info(f"block: {block.__dict__}")
                if block.typee == "image":
                    if block.x0 < page_rect.x0 or block.x1 > page_rect.x1 or block.y0 < page_rect.y0 or block.y1 > page_rect.y1:
                        logging.warn(f"block rect out of range: {block}")
                        continue
                    rect = fitz.Rect(block.x0, block.y0, block.x1, block.y1)
                    with tempfile.NamedTemporaryFile(suffix='.png', prefix='tmp') as tmp:
                        logging.info(
                            f"crop image page {page_index} block {block_num} name {tmp.name}")
                crop_rect(page_image, tmp.name, page_rect, rect)
                logging.info(
                    f"crop done page {page_index} block {block_num}")
                data = tmp.read()
                storage.save(block.pix_path, data=data)
                logging.info(
                    f"save done page {page_index} block {block_num}")
        db.session.commit()
        return {'result': 'ok'}, 200


docFields = {
    "id": fields.Integer,
    "name": fields.String,
    "path": fields.String,
    "page_cnt": fields.Integer,
    "created_at": fields.DateTime,
    "updated_at": fields.DateTime,
}


class DocInfo(Resource):
    def get(self):
        doc = db.session.query(Document).first()
        return marshal(doc, docFields)


api.add_resource(Check, '/check')
api.add_resource(AddDoc, '/addDoc')
api.add_resource(DocInfo, '/docInfo')
