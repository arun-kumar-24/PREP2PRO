from flask import Flask # type: ignore
from app.resume.routes import resume_bp
from app.user.routes import user_bp
from app.testing.routes import test_bp
from app.interview.routes import interview_bp
from app.config import Config

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config) 

    # Register Blueprints
    app.register_blueprint(resume_bp, url_prefix='/resume')
    app.register_blueprint(user_bp, url_prefix='/user')
    app.register_blueprint(test_bp,url_prefix='/testing')
    app.register_blueprint(interview_bp,url_prefix='/interview')

    return app
