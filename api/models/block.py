from extensions.ext_database import db
from typing import List
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy import desc
from sqlalchemy.exc import IntegrityError


class Document(db.Model):
    __tablename__ = "documents"
    __table_args__ = (
        db.UniqueConstraint("path", name='unique_path'),
    )
    id = db.Column(db.Integer, autoincrement=True,
                   primary_key=True, nullable=False)
    name = db.Column(db.String(255), nullable=False)
    path = db.Column(db.String(255), nullable=False, unique=True)
    page_cnt = db.Column(db.Integer, nullable=False)
    created_at = db.Column(db.DateTime, nullable=False,
                           server_default=db.text('CURRENT_TIMESTAMP(0)'))
    updated_at = db.Column(db.DateTime, nullable=False,
                           server_default=db.text('CURRENT_TIMESTAMP(0)'))

    def page_by_num(self, num):
        return db.session.query(Page).filter(Page.doc_id == self.id, Page.page_num == num).first()


class Page(db.Model):
    __tablename__ = "pages"
    __table_args__ = (
        db.UniqueConstraint("doc_id", "page_num", name='unique_doc_pagenum'),
    )
    id = db.Column(db.Integer, autoincrement=True,
                   primary_key=True, nullable=False)
    page_num = db.Column(db.Integer)
    block_cnt = db.Column(db.Integer)
    doc_id = db.Column(db.Integer, db.ForeignKey('documents.id'))
    x0 = db.Column(db.Float)
    x1 = db.Column(db.Float)
    y0 = db.Column(db.Float)
    y1 = db.Column(db.Float)
    created_at = db.Column(db.DateTime, nullable=False,
                           server_default=db.text('CURRENT_TIMESTAMP(0)'))
    updated_at = db.Column(db.DateTime, nullable=False,
                           server_default=db.text('CURRENT_TIMESTAMP(0)'))

    def block_by_num(self, num):
        return db.session.query(Block).filter(Block.page_id == self.id, Block.block_num == num).first()

    @property
    def doc(self):
        return db.session.query(Document).filter(Document.id == self.id).first()


class Block(db.Model):
    __tablename__ = "blocks"
    __table_args__ = (
        db.UniqueConstraint("doc_id", "page_id", "block_num",
                            name='unique_doc_page_blocknum'),
    )
    id = db.Column(db.Integer, autoincrement=True,
                   primary_key=True, nullable=False)
    x0 = db.Column(db.Float)
    x1 = db.Column(db.Float)
    y0 = db.Column(db.Float)
    y1 = db.Column(db.Float)
    block_num = db.Column(db.Integer)
    page_id = db.Column(db.Integer, db.ForeignKey('pages.id'))
    doc_id = db.Column(db.Integer, db.ForeignKey('documents.id'))
    typee = db.Column(db.String(255))
    text = db.Column(db.Text)
    created_at = db.Column(db.DateTime, nullable=False,
                           server_default=db.text('CURRENT_TIMESTAMP(0)'))
    updated_at = db.Column(db.DateTime, nullable=False,
                           server_default=db.text('CURRENT_TIMESTAMP(0)'))

    @property
    def page(self):
        return db.session.query(Page).filter(Page.id == self.page_id).first()

    @property
    def doc(self):
        return db.session.query(Document).filter(Document.id == self.doc_id).first()

    @property
    def pix_path(self):
        return f"image/{self.doc.name}_page{self.page.page_num}_block{self.block_num}.png"

    def is_small_image(self, rate=10):
        if self.typee != "image":
            return False
        page_width = self.page.x1 - self.page.x0
        image_width = self.x1 - self.x0
        return (page_width/image_width) > rate

    def relevant(self):
        rel = []
        if self.typee == "text":
            try:
                block_before = db.session.query(Block).filter(
                    Block.doc_id == self.doc_id, Block.page_id == self.page_id, Block.typee == "image", Block.block_num < self.block_num) \
                    .order_by(desc(Block.block_num)).first()
            except Exception as ex:
                pass

            try:
                block_after = db.session.query(Block).filter(
                    Block.doc_id == self.doc_id, Block.page_id == self.page_id, Block.typee == "image", Block.block_num > self.block_num) \
                    .order_by(Block.block_num).first()
            except Exception as ex:
                pass

            blocks = [block_before, block_after]
            rel = [b for b in blocks if not None]
            for b in rel:
                if b.is_small_image():
                    if self.x0 > b.x1:
                        return [b]
            return rel

        if self.typee == 'image':
            try:
                block_before = db.session.query(Block).filter(
                    Block.doc_id == self.doc_id, Block.page_id == self.page_id, Block.typee == "text", Block.block_num < self.block_num) \
                    .order_by(desc(Block.block_num)).first()
            except Exception as ex:
                pass

            try:
                block_after = db.session.query(Block).filter(
                    Block.doc_id == self.doc_id, Block.page_id == self.page_id, Block.typee == "text", Block.block_num > self.block_num) \
                    .order_by(Block.block_num).first()
            except Exception as ex:
                pass

            blocks = [block_after, block_before]
            rel = [b for b in blocks if not None]
            if self.is_small_image():
                for b in rel:
                    if b.x0 > self.x1:
                        return [b]
            return rel


def update_object_flush(obj, **kwargs):
    for field, value in kwargs.items():
        if hasattr(obj, value):
            setattr(obj, field, value)
    db.session.flush()
    return obj
