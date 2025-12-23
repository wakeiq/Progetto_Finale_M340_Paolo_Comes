from flask import Flask
import os
from dotenv import load_dotenv
from routes.base import base as bp_base
from routes.admin import admin as bp_admin
from routes.auth import auth as bp_auth
from models.connection import db
from flask_migrate import Migrate
from flask_login import LoginManager
from models.model import User, init_db

load_dotenv()

app = Flask(__name__)

app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('SQLALCHEMY_DATABASE_URI', 'sqlite:///labo.db')
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'chiave-segreta-per-sessioni-cambiala-in-produzione')

db.init_app(app)

migrate = Migrate(app, db)

login_manager = LoginManager()
login_manager.login_view = 'auth.login'
login_manager.init_app(app)

@login_manager.user_loader
def load_user(user_id):
    """
    Carica l'utente per Flask-Login
    """
    stmt = db.select(User).filter_by(id=user_id)
    user = db.session.execute(stmt).scalar_one_or_none()
    return user
app.register_blueprint(bp_base)
app.register_blueprint(bp_auth)
app.register_blueprint(bp_admin, url_prefix='/admin')
with app.app_context():
    init_db()

if __name__ == '__main__':
    host = os.getenv('HOST', 'localhost')
    port = int(os.getenv('PORT', 5000))
    print(f"\nServer Flask avviato:")
    print(f"Aprire il browser su: http://{host}:{port}")
    print("\nCredenziali admin:")
    print(f"  Email: {os.getenv('ADMIN_EMAIL', 'admin@example.com')}")
    print(f"  Password: {os.getenv('ADMIN_PASSWORD', 'password')}")
    print("\n")
    
    app.run(debug=True, host=host, port=port)
