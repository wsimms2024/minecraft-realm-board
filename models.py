from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()


class Friend(db.Model):
    __tablename__ = "friends"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, unique=True)


class Location(db.Model):
    __tablename__ = "locations"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    x = db.Column(db.Integer, nullable=False, default=0)
    y = db.Column(db.Integer, nullable=False, default=64)
    z = db.Column(db.Integer, nullable=False, default=0)
    note = db.Column(db.Text, default="")


class BaseInfo(db.Model):
    __tablename__ = "base_info"
    id = db.Column(db.Integer, primary_key=True)
    seed = db.Column(db.String(200), default="")


class Idea(db.Model):
    __tablename__ = "ideas"
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    category = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, default="")


class Project(db.Model):
    __tablename__ = "projects"
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    category = db.Column(db.String(100), nullable=False, default="")
    description = db.Column(db.Text, default="")
    proposed_by_id = db.Column(db.Integer, db.ForeignKey("friends.id"), nullable=True)
    is_on_board = db.Column(db.Boolean, nullable=False, default=False)
    # for proposals: status is irrelevant; for board: not_started / in_progress / done
    status = db.Column(db.String(50), default="not_started")
    image_url = db.Column(db.String(500), default="")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    proposed_by = db.relationship("Friend", foreign_keys=[proposed_by_id])
    votes = db.relationship("Vote", backref="project", cascade="all, delete-orphan")
    materials = db.relationship(
        "MaterialItem",
        backref="project",
        cascade="all, delete-orphan",
        order_by="MaterialItem.id",
    )
    assignments = db.relationship(
        "ProjectAssignment", backref="project", cascade="all, delete-orphan"
    )


class Vote(db.Model):
    __tablename__ = "votes"
    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey("projects.id"), nullable=False)
    friend_id = db.Column(db.Integer, db.ForeignKey("friends.id"), nullable=False)
    friend = db.relationship("Friend")
    __table_args__ = (db.UniqueConstraint("project_id", "friend_id"),)


class MaterialItem(db.Model):
    __tablename__ = "material_items"
    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey("projects.id"), nullable=False)
    text = db.Column(db.String(300), nullable=False)
    gathered = db.Column(db.Boolean, default=False)


class ProjectAssignment(db.Model):
    __tablename__ = "project_assignments"
    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey("projects.id"), nullable=False)
    friend_id = db.Column(db.Integer, db.ForeignKey("friends.id"), nullable=False)
    friend = db.relationship("Friend")
    __table_args__ = (db.UniqueConstraint("project_id", "friend_id"),)
