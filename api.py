from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session
from typing import List
import os
from models import User, Application, Permission, get_session, init_db

app = FastAPI(title="Identity & Access Validation API")

# Database dependency
def get_db():
    db_url = os.getenv('DATABASE_URL', 'postgresql://localhost/identity_management')
    engine = init_db(db_url)
    session = get_session(engine)
    try:
        yield session
    finally:
        session.close()

# Response Model
class AccessResponse(BaseModel):
    username: str
    application: str
    access: bool
    permissions: List[str]

# API Endpoints
@app.get("/")
def root():
    return {
        "service": "Identity & Access Validation API",
        "version": "1.0",
        "endpoints": {
            "check_access": "/access/{username}/{application}",
            "list_users": "/users",
            "list_applications": "/applications"
        }
    }

@app.get("/access/{username}/{application}", response_model=AccessResponse)
def check_access(username: str, application: str, db: Session = Depends(get_db)):
    """
    Check if a user has access to an application and return their permissions.
    
    Example: /access/alice@example.com/Google
    Returns: username, application, access (true/false), permissions ["Docs: Read", "Sheets: Write"]
    """
    # Find user
    user = db.query(User).filter_by(username=username).first()
    if not user:
        raise HTTPException(status_code=404, detail=f"User '{username}' not found")
    
    # Find application
    app = db.query(Application).filter_by(name=application).first()
    if not app:
        raise HTTPException(status_code=404, detail=f"Application '{application}' not found")
    
    # Check access via groups
    has_access = False
    all_permissions = set()
    
    for group in user.groups:
        if app in group.applications:
            has_access = True
            
            # Collect permissions from this group
            for permission in group.permissions:
                all_permissions.add(permission)
    
    # Also check direct user permissions (if any)
    for permission in user.permissions:
        all_permissions.add(permission)
    
    # Format permissions as "Resource: Action" (e.g., "Docs: Read")
    permission_strings = [
        f"{p.resource}: {p.action}"
        for p in all_permissions
    ]
    
    # Sort permissions for consistent output
    permission_strings.sort()
    
    return AccessResponse(
        username=username,
        application=application,
        access=has_access,
        permissions=permission_strings
    )

@app.get("/users")
def list_users(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    """List all users in the system"""
    users = db.query(User).offset(skip).limit(limit).all()
    return [
        {
            "username": u.username,
            "email": u.email,
            "groups": [g.name for g in u.groups],
            "roles": [r.name for r in u.roles]
        }
        for u in users
    ]

@app.get("/users/{username}")
def get_user_details(username: str, db: Session = Depends(get_db)):
    """Get detailed information about a specific user"""
    user = db.query(User).filter_by(username=username).first()
    if not user:
        raise HTTPException(status_code=404, detail=f"User '{username}' not found")
    
    # Get all applications the user has access to
    accessible_apps = set()
    for group in user.groups:
        for app in group.applications:
            accessible_apps.add(app)
    
    return {
        "username": user.username,
        "email": user.email,
        "groups": [{"id": g.id, "name": g.name} for g in user.groups],
        "roles": [{"id": r.id, "name": r.name} for r in user.roles],
        "direct_permissions": [p.name for p in user.permissions],
        "accessible_applications": [a.name for a in accessible_apps]
    }

@app.get("/applications")
def list_applications(db: Session = Depends(get_db)):
    """List all applications in the system"""
    apps = db.query(Application).all()
    return [
        {
            "name": a.name,
            "description": a.description,
            "authorized_groups": [g.name for g in a.groups]
        }
        for a in apps
    ]

@app.get("/groups")
def list_groups(db: Session = Depends(get_db)):
    """List all groups in the system"""
    from models import Group
    groups = db.query(Group).all()
    return [
        {
            "name": g.name,
            "user_count": len(g.users),
            "permissions": [p.name for p in g.permissions],
            "applications": [a.name for a in g.applications]
        }
        for g in groups
    ]

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)