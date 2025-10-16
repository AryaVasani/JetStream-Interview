import sys
from models import init_db, get_session, User, Application

def check_access(username: str, application_name: str):
    """Check if user has access to application and print permissions"""
    
    # Initialize database
    engine = init_db()
    session = get_session(engine)
    
    try:
        # Find user
        user = session.query(User).filter_by(username=username).first()
        if not user:
            print(f"Error: User '{username}' not found")
            return
        
        # Find application
        app = session.query(Application).filter_by(name=application_name).first()
        if not app:
            print(f"Error: Application '{application_name}' not found")
            return
        
        # Check access via groups
        has_access = False
        all_permissions = set()
        
        for group in user.groups:
            if app in group.applications:
                has_access = True
                
                # Collect permissions from this group
                for permission in group.permissions:
                    all_permissions.add(permission)
        
        # Also check direct user permissions
        for permission in user.permissions:
            all_permissions.add(permission)
        
        # Format permissions as list of strings
        permission_list = [f"{p.resource}:{p.action}" for p in all_permissions]
        permission_list.sort()
        
        # Print output in the exact format from the prompt
        if has_access:
            print(f"User {username} has access to {application_name} → Permissions: {permission_list}")
        else:
            print(f"User {username} does NOT have access to {application_name}")
        
    finally:
        session.close()


def main():
    """Main entry point for CLI"""
    if len(sys.argv) != 3:
        print("Usage: python check_access.py <username> <application>")
        print("\nExamples:")
        print("  python check_access.py alice@example.com Google")
        print("  python check_access.py bob@example.com Slack")
        print("  python check_access.py connie@example.com Google")
        sys.exit(1)
    
    username = sys.argv[1]
    application = sys.argv[2]
    
    check_access(username, application)


if __name__ == "__main__":
    main()