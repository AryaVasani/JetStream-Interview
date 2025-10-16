import os
import requests
from dotenv import load_dotenv
from models import User, Group, Role, Permission, Application, get_session, init_db

load_dotenv()

class Auth0SyncService:
    def __init__(self, db_session):
        # Get domain from env and clean it
        domain_from_env = os.getenv('AUTH0_DOMAIN', '')
        self.domain = domain_from_env.replace('https://', '').replace('http://', '')
        self.client_id = os.getenv('AUTH0_CLIENT_ID')
        self.client_secret = os.getenv('AUTH0_CLIENT_SECRET')
        self.session = db_session
        self.access_token = None
    
    def get_access_token(self):
        """Get Auth0 Management API token"""
        print("Getting Auth0 access token...")
        
        # Clean domain - remove https:// if present
        domain = self.domain.replace('https://', '').replace('http://', '')
        
        url = f"https://{domain}/oauth/token"
        payload = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "audience": f"https://{domain}/api/v2/",
            "grant_type": "client_credentials"
        }
        
        print(f"Token URL: {url}")
        print(f"Audience: https://{domain}/api/v2/")
        
        response = requests.post(url, json=payload)
        
        if response.status_code == 200:
            self.access_token = response.json()['access_token']
            print("✓ Access token obtained")
            return True
        else:
            print(f"✗ Failed to get token (Status {response.status_code}): {response.text}")
            return False
    
    def get_users(self, limit=100):
        """Fetch users from Auth0"""
        print(f"Fetching up to {limit} users from Auth0...")
        
        url = f"https://{self.domain}/api/v2/users"
        headers = {"Authorization": f"Bearer {self.access_token}"}
        params = {"per_page": limit}
        
        response = requests.get(url, headers=headers, params=params)
        
        if response.status_code == 200:
            users = response.json()
            print(f"✓ Found {len(users)} users")
            return users
        else:
            print(f"✗ Failed to get users: {response.text}")
            return []
    
    def sync_users(self, limit=100):
        """Sync users from Auth0 to database"""
        if not self.get_access_token():
            return 0
        
        auth0_users = self.get_users(limit)
        user_count = 0
        
        for auth0_user in auth0_users:
            # Extract user info
            user_id = auth0_user.get('user_id')
            email = auth0_user.get('email', f"{user_id}@example.com")
            name = auth0_user.get('name', email.split('@')[0])
            
            # Check if user exists
            db_user = self.session.query(User).filter_by(idp_id=user_id).first()
            
            if not db_user:
                db_user = User(
                    username=name,
                    email=email,
                    idp_id=user_id
                )
                self.session.add(db_user)
                print(f"  + Added user: {name}")
            else:
                print(f"  ✓ User exists: {name}")
            
            user_count += 1
        
        self.session.commit()
        print(f"✓ Synced {user_count} users")
        return user_count
    
    def create_sample_groups(self):
        """Create sample groups based on Auth0 users"""
        print("\nCreating sample groups...")
        
        groups_data = [
            ("Admins", "Administrator users"),
            ("Editors", "Editor users"),
            ("Viewers", "Viewer users")
        ]
        
        for group_name, description in groups_data:
            db_group = self.session.query(Group).filter_by(name=group_name).first()
            
            if not db_group:
                db_group = Group(
                    name=group_name,
                    idp_id=f"group_{group_name.lower()}"
                )
                self.session.add(db_group)
                print(f"  + Created group: {group_name}")
            
            # Also create matching role
            db_role = self.session.query(Role).filter_by(name=group_name).first()
            if not db_role:
                db_role = Role(
                    name=group_name,
                    description=description
                )
                self.session.add(db_role)
        
        self.session.commit()
        print("✓ Groups and roles created")
    
    def assign_users_to_groups(self):
        """Assign users to groups based on their names"""
        print("\nAssigning users to groups...")
        
        users = self.session.query(User).all()
        
        for user in users:
            username_lower = user.username.lower()
            
            # Assign based on username
            if 'alice' in username_lower or 'admin' in username_lower:
                group = self.session.query(Group).filter_by(name='Admins').first()
                role = self.session.query(Role).filter_by(name='Admins').first()
            elif 'bob' in username_lower or 'editor' in username_lower:
                group = self.session.query(Group).filter_by(name='Editors').first()
                role = self.session.query(Role).filter_by(name='Editors').first()
            else:
                group = self.session.query(Group).filter_by(name='Viewers').first()
                role = self.session.query(Role).filter_by(name='Viewers').first()
            
            if group and group not in user.groups:
                user.groups.append(group)
                print(f"  + Assigned {user.username} → {group.name}")
            
            if role and role not in user.roles:
                user.roles.append(role)
        
        self.session.commit()
        print("✓ Users assigned to groups")
    
    def create_sample_applications(self):
        """Create sample applications"""
        print("\nCreating sample applications...")
        
        apps_data = [
            ("Google", "Google Workspace"),
            ("Slack", "Slack Workspace")
        ]
        
        for app_name, description in apps_data:
            db_app = self.session.query(Application).filter_by(name=app_name).first()
            
            if not db_app:
                db_app = Application(
                    name=app_name,
                    description=description
                )
                self.session.add(db_app)
                print(f"  + Created app: {app_name}")
        
        self.session.commit()
        print("✓ Applications created")
    
    def assign_groups_to_apps(self):
        """Assign groups to applications"""
        print("\nAssigning groups to applications...")
        
        # Google: Admins and Editors
        google_app = self.session.query(Application).filter_by(name='Google').first()
        if google_app:
            admins = self.session.query(Group).filter_by(name='Admins').first()
            editors = self.session.query(Group).filter_by(name='Editors').first()
            
            if admins and admins not in google_app.groups:
                google_app.groups.append(admins)
                print(f"  + Google ← Admins")
            
            if editors and editors not in google_app.groups:
                google_app.groups.append(editors)
                print(f"  + Google ← Editors")
        
        # Slack: Only Admins
        slack_app = self.session.query(Application).filter_by(name='Slack').first()
        if slack_app and admins:
            if admins not in slack_app.groups:
                slack_app.groups.append(admins)
                print(f"  + Slack ← Admins")
        
        self.session.commit()
        print("✓ Groups assigned to applications")
    
    def create_sample_permissions(self):
        """Create sample permissions"""
        print("\nCreating sample permissions...")
        
        sample_permissions = [
            ("Docs:Read", "Docs", "Read"),
            ("Docs:Write", "Docs", "Write"),
            ("Sheets:Read", "Sheets", "Read"),
            ("Sheets:Write", "Sheets", "Write"),
            ("Slides:Read", "Slides", "Read"),
            ("Slides:Write", "Slides", "Write"),
        ]
        
        for perm_name, resource, action in sample_permissions:
            existing = self.session.query(Permission).filter_by(name=perm_name).first()
            if not existing:
                permission = Permission(name=perm_name, resource=resource, action=action)
                self.session.add(permission)
        
        self.session.commit()
        print("✓ Permissions created")
    
    def assign_permissions_to_groups(self):
        """Assign permissions to groups"""
        print("\nAssigning permissions to groups...")
        
        groups = self.session.query(Group).all()
        permissions = self.session.query(Permission).all()
        
        for group in groups:
            if "admin" in group.name.lower():
                # Admins get all permissions
                group.permissions = permissions
                print(f"  + {group.name} → All permissions")
            elif "editor" in group.name.lower():
                # Editors get write permissions
                group.permissions = [p for p in permissions if "Write" in p.name]
                print(f"  + {group.name} → Write permissions")
            else:
                # Viewers get read permissions
                group.permissions = [p for p in permissions if "Read" in p.name]
                print(f"  + {group.name} → Read permissions")
        
        self.session.commit()
        print("✓ Permissions assigned to groups")


def run_sync():
    """Main sync function"""
    print("=" * 60)
    print("  AUTH0 IDENTITY SYNC SERVICE")
    print("=" * 60)
    
    # Load environment
    load_dotenv()
    
    domain = os.getenv('AUTH0_DOMAIN')
    client_id = os.getenv('AUTH0_CLIENT_ID')
    client_secret = os.getenv('AUTH0_CLIENT_SECRET')
    db_url = os.getenv('DATABASE_URL')
    
    if not domain or not client_id or not client_secret:
        print("✗ Error: Missing Auth0 credentials in .env file")
        print("  Please set AUTH0_DOMAIN, AUTH0_CLIENT_ID, and AUTH0_CLIENT_SECRET")
        print("\nExample .env file:")
        print("  AUTH0_DOMAIN=https://dev-23dbcw4xd80l7pot.us.auth0.com")
        print("  AUTH0_CLIENT_ID=your_client_id")
        print("  AUTH0_CLIENT_SECRET=your_client_secret")
        return
    
    print(f"\nAuth0 Domain: {domain}")
    print(f"Database: {db_url}\n")
    
    # Initialize database
    engine = init_db(db_url)
    session = get_session(engine)
    
    # Run sync
    sync_service = Auth0SyncService(session)
    
    try:
        # Sync users from Auth0
        sync_service.sync_users(limit=100)
        
        # Create groups and roles
        sync_service.create_sample_groups()
        
        # Assign users to groups
        sync_service.assign_users_to_groups()
        
        # Create applications
        sync_service.create_sample_applications()
        
        # Assign groups to applications
        sync_service.assign_groups_to_apps()
        
        # Create permissions
        sync_service.create_sample_permissions()
        
        # Assign permissions to groups
        sync_service.assign_permissions_to_groups()
        
        print("\n" + "=" * 60)
        print("  ✓ SYNC COMPLETED SUCCESSFULLY!")
        print("=" * 60)
        
        # Summary
        print("\nSummary:")
        print(f"  Users: {session.query(User).count()}")
        print(f"  Groups: {session.query(Group).count()}")
        print(f"  Roles: {session.query(Role).count()}")
        print(f"  Applications: {session.query(Application).count()}")
        print(f"  Permissions: {session.query(Permission).count()}")
        
    except Exception as e:
        print(f"\n✗ Error during sync: {e}")
        import traceback
        traceback.print_exc()
    finally:
        session.close()


if __name__ == "__main__":
    run_sync()