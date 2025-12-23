from models.connection import db
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
import os
from dotenv import load_dotenv
load_dotenv()
class User(UserMixin, db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), default='user', nullable=False)
    vm_requests = db.relationship('VMRequest', backref='user_ref', lazy=True)
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    def has_role(self, role_name):
        return self.role == role_name
    def __repr__(self):
        return f'<User {self.username}>'

class VMRequest(db.Model):
    __tablename__ = 'vm_requests'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    vm_type = db.Column(db.String(20), nullable=False)
    status = db.Column(db.String(20), default='PENDING', nullable=False)
    ip = db.Column(db.String(50), nullable=True)
    vm_user = db.Column(db.String(50), nullable=True)
    vm_password = db.Column(db.String(255), nullable=True)
    vm_id_proxmox = db.Column(db.String(50), nullable=True)
    def __repr__(self):
        return f'<VMRequest {self.id} - {self.vm_type} - {self.status}>'
    
def init_db():
    db.create_all()
    admin_email = os.getenv('ADMIN_EMAIL', 'admin@example.com')
    admin_password = os.getenv('ADMIN_PASSWORD', 'admin')
    admin_user = User.query.filter_by(email=admin_email).first()
    if not admin_user:
        admin_user = User(
            username='admin',
            email=admin_email,
            role='admin'
        )
        admin_user.set_password(admin_password)
        db.session.add(admin_user)
        db.session.commit()
        print(f"Utente admin creato: {admin_email} / {admin_password}")

