#!/usr/bin/env python3
"""
Zotero Setup Helper

This script helps you set up the Zotero integration for the knowledge pipeline.
It guides you through:
1. Getting your Zotero API credentials
2. Installing the Actions & Tags plugin
3. Setting up environment variables
4. Testing the connection
"""

import os
import sys
from pathlib import Path

# Add src to path for imports
current_dir = Path(__file__).parent
src_dir = current_dir.parent / "src"
sys.path.insert(0, str(src_dir))

def print_header(title: str):
    """Print a formatted header."""
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")

def print_step(step: int, title: str):
    """Print a formatted step."""
    print(f"\n📋 Step {step}: {title}")
    print("-" * 40)

def get_user_input(prompt: str, required: bool = True) -> str:
    """Get user input with validation."""
    while True:
        value = input(f"{prompt}: ").strip()
        if value or not required:
            return value
        print("❌ This field is required. Please try again.")

def test_zotero_connection(user_id: str, api_key: str, library_type: str = 'user'):
    """Test the Zotero connection."""
    try:
        from core.zotero_client import ZoteroClient
        
        client = ZoteroClient(user_id, library_type, api_key)
        
        # Test basic functionality
        items = client.get_items_to_process(limit=1)
        
        print(f"✅ Connection successful!")
        print(f"   Found {len(items)} items tagged with '/to_process'")
        
        return True
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
        print("   Make sure you've installed pyzotero: pip install pyzotero")
        return False
    except Exception as e:
        print(f"❌ Connection failed: {e}")
        return False

def main():
    """Main setup flow."""
    
    print_header("🔧 Zotero Integration Setup")
    print("\nThis script will help you set up Zotero integration for the knowledge pipeline.")
    print("You'll need:")
    print("• A Zotero account")
    print("• API access enabled")
    print("• The Actions & Tags plugin (optional but recommended)")
    
    proceed = input("\nReady to start? (y/n): ").strip().lower()
    if proceed != 'y':
        print("Setup cancelled.")
        return
    
    # Step 1: Get API credentials
    print_step(1, "Get Your Zotero API Credentials")
    print("\n1. Go to: https://www.zotero.org/settings/keys")
    print("2. Click 'Create new private key'")
    print("3. Give it a name (e.g., 'Knowledge Pipeline')")
    print("4. Under 'Personal Library', check 'Allow library access' and 'Allow write access'")
    print("5. Click 'Save Key'")
    print("6. Copy your API key (you won't see it again!)")
    print("\nAlso note your User ID (shown at the top of the keys page)")
    
    input("\nPress Enter when you have your credentials ready...")
    
    # Get credentials
    user_id = get_user_input("Enter your Zotero User ID")
    api_key = get_user_input("Enter your Zotero API Key")
    
    # Step 2: Plugin recommendation
    print_step(2, "Install Actions & Tags Plugin (Recommended)")
    print("\nThe Actions & Tags plugin automates the workflow:")
    print("• Automatically adds '/to_process' tag to new items")
    print("• Enables event-driven processing")
    print("\nTo install:")
    print("1. Download from: https://github.com/windingwind/zotero-actions-tags/releases")
    print("2. In Zotero: Tools → Add-ons → Install Add-on From File")
    print("3. Select the downloaded .xpi file")
    print("4. Restart Zotero")
    
    plugin_installed = input("\nDid you install the Actions & Tags plugin? (y/n): ").strip().lower() == 'y'
    
    if plugin_installed:
        print("\nGreat! You can configure it later in Zotero:")
        print("• Tools → Actions & Tags → Settings")
        print("• Add rule: 'When item added' → 'Add tag: /to_process'")
    
    # Step 3: Test connection
    print_step(3, "Test Connection")
    print("Testing your Zotero connection...")
    
    if test_zotero_connection(user_id, api_key):
        # Step 4: Set up environment variables
        print_step(4, "Set Up Environment Variables")
        
        # Create .env file
        env_file = current_dir.parent / ".env"
        
        env_content = f"""# Zotero API Configuration
ZOTERO_USER_ID={user_id}
ZOTERO_API_KEY={api_key}
ZOTERO_LIBRARY_TYPE=user

# Optional: For group libraries
# ZOTERO_LIBRARY_TYPE=group
# ZOTERO_GROUP_ID=your_group_id
"""
        
        try:
            with open(env_file, "w") as f:
                f.write(env_content)
            
            print(f"✅ Created .env file: {env_file}")
            print("\nTo use these variables in your shell, run:")
            print(f"   source {env_file}")
            
        except Exception as e:
            print(f"❌ Could not create .env file: {e}")
            print("\nManually set these environment variables:")
            print(f"   export ZOTERO_USER_ID='{user_id}'")
            print(f"   export ZOTERO_API_KEY='{api_key}'")
            print(f"   export ZOTERO_LIBRARY_TYPE='user'")
        
        # Step 5: Next steps
        print_step(5, "Next Steps")
        print("\n✅ Zotero integration is ready!")
        print("\nWhat you can do now:")
        print("• Add some PDFs to your Zotero library")
        print("• Tag them with '/to_process' (or set up auto-tagging)")
        print("• Run the knowledge pipeline to process them")
        print("\nExample usage:")
        print("   python -c \"from src.core.zotero_client import create_zotero_client; client = create_zotero_client(); print(f'Items to process: {len(client.get_items_to_process())}')\"\n")
        
    else:
        print("\n❌ Connection test failed. Please check your credentials and try again.")

if __name__ == "__main__":
    main()