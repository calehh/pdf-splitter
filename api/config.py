# -*- coding:utf-8 -*-
import os
from datetime import timedelta

import dotenv

from extensions.ext_database import db
from extensions.ext_redis import redis_client

dotenv.load_dotenv()

DEFAULTS = {
    'COOKIE_HTTPONLY': 'True',
    'COOKIE_SECURE': 'False',
    'COOKIE_SAMESITE': 'None',
    'DB_USERNAME': 'postgres',
    'DB_PASSWORD': 'vulcan123456',
    'DB_HOST': 'localhost',
    'DB_PORT': '5432',
    'DB_DATABASE': 'indexer',
    'REDIS_HOST': 'localhost',
    'REDIS_PORT': '6379',
    'REDIS_DB': '0',
    'REDIS_USE_SSL': 'False',
    'REDIS_USERNAME': '',
    'REDIS_PASSWORD': 'vulcan123456',
    'SESSION_REDIS_HOST': 'localhost',
    'SESSION_REDIS_PORT': '6379',
    'SESSION_REDIS_DB': '2',
    'SESSION_REDIS_USE_SSL': 'False',
    'SESSION_REDIS_USERNAME': '',
    'SESSION_REDIS_PASSWORD': 'vulcan123456',
    'STORAGE_TYPE': 'local',
    'STORAGE_LOCAL_PATH': '/Users/houmingyu/Documents/chatgpt/pdf-indexer/docker/volumes/app/storage',
    'SESSION_TYPE': 'redis',
    'SESSION_PERMANENT': 'True',
    'SESSION_USE_SIGNER': 'True',
    'DEPLOY_ENV': 'PRODUCTION',
    'SQLALCHEMY_POOL_SIZE': 10,
    'SQLALCHEMY_ECHO': 'False',
    'LOG_LEVEL': 'DEBUG',
    'SECRET_KEY': 'sk-9f73s3ljTXVcMT3Blb3ljTqtsKiGHXVcMT3BlbkFJLK7U',
    'WEB_API_CORS_ALLOW_ORIGINS': '*',
    'CONSOLE_CORS_ALLOW_ORIGINS': '*',
}


def get_env(key):
    return os.environ.get(key, DEFAULTS.get(key))


def get_bool_env(key):
    return get_env(key).lower() == 'true'


def get_cors_allow_origins(env, default):
    cors_allow_origins = []
    if get_env(env):
        for origin in get_env(env).split(','):
            cors_allow_origins.append(origin)
    else:
        cors_allow_origins = [default]

    return cors_allow_origins


class Config:
    """Application configuration class."""

    def __init__(self):
        # app settings
        self.CONSOLE_URL = get_env('CONSOLE_URL')
        self.API_URL = get_env('API_URL')
        self.APP_URL = get_env('APP_URL')
        self.CURRENT_VERSION = "0.0.1"
        self.COMMIT_SHA = get_env('COMMIT_SHA')
        self.EDITION = "SELF_HOSTED"
        self.DEPLOY_ENV = get_env('DEPLOY_ENV')
        self.TESTING = False
        self.LOG_LEVEL = get_env('LOG_LEVEL')

        # Your App secret key will be used for securely signing the session cookie
        # Make sure you are changing this key for your deployment with a strong key.
        # You can generate a strong key using `openssl rand -base64 42`.
        # Alternatively you can set it with `SECRET_KEY` environment variable.
        self.SECRET_KEY = get_env('SECRET_KEY')

        # cookie settings
        self.REMEMBER_COOKIE_HTTPONLY = get_bool_env('COOKIE_HTTPONLY')
        self.SESSION_COOKIE_HTTPONLY = get_bool_env('COOKIE_HTTPONLY')
        self.REMEMBER_COOKIE_SAMESITE = get_env('COOKIE_SAMESITE')
        self.SESSION_COOKIE_SAMESITE = get_env('COOKIE_SAMESITE')
        self.REMEMBER_COOKIE_SECURE = get_bool_env('COOKIE_SECURE')
        self.SESSION_COOKIE_SECURE = get_bool_env('COOKIE_SECURE')
        self.PERMANENT_SESSION_LIFETIME = timedelta(days=7)

        # session settings, only support sqlalchemy, redis
        self.SESSION_TYPE = get_env('SESSION_TYPE')
        self.SESSION_PERMANENT = get_bool_env('SESSION_PERMANENT')
        self.SESSION_USE_SIGNER = get_bool_env('SESSION_USE_SIGNER')

        # redis settings
        self.REDIS_HOST = get_env('REDIS_HOST')
        self.REDIS_PORT = get_env('REDIS_PORT')
        self.REDIS_USERNAME = get_env('REDIS_USERNAME')
        self.REDIS_PASSWORD = get_env('REDIS_PASSWORD')
        self.REDIS_DB = get_env('REDIS_DB')
        self.REDIS_USE_SSL = get_bool_env('REDIS_USE_SSL')

        # session redis settings
        self.SESSION_REDIS_HOST = get_env('SESSION_REDIS_HOST')
        self.SESSION_REDIS_PORT = get_env('SESSION_REDIS_PORT')
        self.SESSION_REDIS_USERNAME = get_env('SESSION_REDIS_USERNAME')
        self.SESSION_REDIS_PASSWORD = get_env('SESSION_REDIS_PASSWORD')
        self.SESSION_REDIS_DB = get_env('SESSION_REDIS_DB')
        self.SESSION_REDIS_USE_SSL = get_bool_env('SESSION_REDIS_USE_SSL')

        # storage settings
        self.STORAGE_TYPE = get_env('STORAGE_TYPE')
        self.STORAGE_LOCAL_PATH = get_env('STORAGE_LOCAL_PATH')
        self.S3_ENDPOINT = get_env('S3_ENDPOINT')
        self.S3_BUCKET_NAME = get_env('S3_BUCKET_NAME')
        self.S3_ACCESS_KEY = get_env('S3_ACCESS_KEY')
        self.S3_SECRET_KEY = get_env('S3_SECRET_KEY')
        self.S3_REGION = get_env('S3_REGION')

        # cors settings
        self.CONSOLE_CORS_ALLOW_ORIGINS = get_cors_allow_origins(
            'CONSOLE_CORS_ALLOW_ORIGINS', self.CONSOLE_URL)
        self.WEB_API_CORS_ALLOW_ORIGINS = get_cors_allow_origins(
            'WEB_API_CORS_ALLOW_ORIGINS', '*')

        # database settings
        db_credentials = {
            key: get_env(key) for key in
            ['DB_USERNAME', 'DB_PASSWORD', 'DB_HOST', 'DB_PORT', 'DB_DATABASE']
        }

        self.SQLALCHEMY_DATABASE_URI = f"postgresql://{db_credentials['DB_USERNAME']}:{db_credentials['DB_PASSWORD']}@{db_credentials['DB_HOST']}:{db_credentials['DB_PORT']}/{db_credentials['DB_DATABASE']}"
        self.SQLALCHEMY_ENGINE_OPTIONS = {
            'pool_size': int(get_env('SQLALCHEMY_POOL_SIZE'))}

        self.SQLALCHEMY_ECHO = get_bool_env('SQLALCHEMY_ECHO')


class TestConfig(Config):

    def __init__(self):
        super().__init__()

        self.EDITION = "SELF_HOSTED"
        self.TESTING = True

        db_credentials = {
            key: get_env(key) for key in ['DB_USERNAME', 'DB_PASSWORD', 'DB_HOST', 'DB_PORT']
        }

        # use a different database for testing: dify_test
        self.SQLALCHEMY_DATABASE_URI = f"postgresql://{db_credentials['DB_USERNAME']}:{db_credentials['DB_PASSWORD']}@{db_credentials['DB_HOST']}:{db_credentials['DB_PORT']}/dify_test"
