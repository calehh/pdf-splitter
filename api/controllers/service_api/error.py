from libs.exceptions import BaseHTTPException


class FileNotExistError(BaseHTTPException):
    error_code = 'file_not_exist'
    description = "File not exist"
    code = 403
