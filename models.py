from sqlalchemy import Column, Integer, String, ForeignKey, Table, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker
import os
from dotenv import load_dotenv

# Load environment variables with debugging
print("Loading .env file...")
load_dotenv(verbose=True, override=True)
print(f"DATABASE_URL after load: {os.getenv('DATABASE_URL')}")

Base = declarative_base()

# Junction Tables
user_groups = Table('user_groups', Base.metadata,
    Column('user_id', Integer, ForeignKey('users.id'), primary_key=True),
    Column('group_id', Integer, ForeignKey('groups.id'), primary_key=True)
)

user_roles = Table('user_roles', Base.metadata,
    Column('user_id', Integer, ForeignKey('users.id'), primary_key=True),
    Column('role_id', Integer, ForeignKey('roles.id'), primary_key=True)
)

user_permissions = Table('user_permissions', Base.metadata,
    Column('user_id', Integer, ForeignKey('users.id'), primary_key=True),
    Column('permission_id', Integer, ForeignKey('permissions.id'), primary_key=True)
)

group_permissions = Table('group_permissions', Base.metadata,
    Column('group_id', Integer, ForeignKey('groups.id'), primary_key=True),
    Column('permission_id', Integer, ForeignKey('permissions.id'), primary_key=True)
)

group_applications = Table('group_applications', Base.metadata,
    Column('group_id', Integer, ForeignKey('groups.id'), primary_key=True),
    Column('application_id', Integer, ForeignKey('applications.id'), primary_key=True)
)

# Main Tables
class User(Base):
    __tablename__ = 'users'
    
    id = Column(Integer, primary_key=True)
    username = Column(String, unique=True, nullable=False)
    email = Column(String, unique=True, nullable=False)
    idp_id = Column(String, unique=True, nullable=False)
    
    groups = relationship('Group', secondary=user_groups, back_populates='users')
    roles = relationship('Role', secondary=user_roles, back_populates='users')
    permissions = relationship('Permission', secondary=user_permissions, back_populates='users')

class Group(Base):
    __tablename__ = 'groups'
    
    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True, nullable=False)
    idp_id = Column(String, unique=True, nullable=False)
    
    users = relationship('User', secondary=user_groups, back_populates='groups')
    permissions = relationship('Permission', secondary=group_permissions, back_populates='groups')
    applications = relationship('Application', secondary=group_applications, back_populates='groups')

class Role(Base):
    __tablename__ = 'roles'
    
    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True, nullable=False)
    description = Column(String)
    
    users = relationship('User', secondary=user_roles, back_populates='roles')

class Permission(Base):
    __tablename__ = 'permissions'
    
    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True, nullable=False)
    resource = Column(String, nullable=False)
    action = Column(String, nullable=False)
    
    users = relationship('User', secondary=user_permissions, back_populates='permissions')
    groups = relationship('Group', secondary=group_permissions, back_populates='permissions')

class Application(Base):
    __tablename__ = 'applications'
    
    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True, nullable=False)
    description = Column(String)
    
    groups = relationship('Group', secondary=group_applications, back_populates='applications')

# Database setup
def init_db(database_url=None):
    # Force reload of .env inside the function
    load_dotenv(override=True)
    
    if database_url is None:
        database_url = os.getenv('DATABASE_URL')
        if not database_url:
            raise ValueError(
                "DATABASE_URL not found in environment!\n"
                "Please check your .env file exists and contains:\n"
                "DATABASE_URL=postgresql://postgres:YOUR_PASSWORD@localhost/identity_management"
            )
    
    print(f"Connecting to: {database_url}")
    engine = create_engine(database_url)
    Base.metadata.create_all(engine)
    return engine

def get_session(engine):
    Session = sessionmaker(bind=engine)
    return Session()