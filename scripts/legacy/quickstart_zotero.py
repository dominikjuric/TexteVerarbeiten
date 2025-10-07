#!/usr/bin/env python3
"""
Zotero Integration Quick Start

Run this script to set up the Zotero integration step by step.
"""

import os
import sys
from pathlib import Path

def main():
    print("🔧 Zotero Integration Setup")
    print("=" * 50)
    
    print("\n📋 What you need:")
    print("1. A Zotero account with some PDFs")
    print("2. API credentials from Zotero") 
    print("3. Optional: Actions & Tags plugin for automation")
    
    print("\n🚀 Quick Setup Steps:")
    print("\n1️⃣ Get your Zotero API key:")
    print("   → Go to: https://www.zotero.org/settings/keys")
    print("   → Create new private key with library access")
    print("   → Copy your User ID and API key")
    
    print("\n2️⃣ Set environment variables:")
    print("   export ZOTERO_USER_ID='your_user_id'")
    print("   export ZOTERO_API_KEY='your_api_key'")
    
    print("\n3️⃣ Install Actions & Tags plugin (recommended):")
    print("   → Download: https://github.com/windingwind/zotero-actions-tags/releases")
    print("   → Install in Zotero: Tools → Add-ons → Install Add-on From File")
    print("   → Configure: Add rule 'When item added' → 'Add tag: /to_process'")
    
    print("\n4️⃣ Test the integration:")
    print("   python src/core/zotero_client.py")
    
    print("\n5️⃣ Process your first documents:")
    print("   python src/core/dispatcher.py")
    
    print("\n📖 For detailed setup, run:")
    print("   python setup_zotero.py")
    
    print("\n✨ Next steps after Zotero setup:")
    print("• Install Nougat for scientific PDF processing")
    print("• Set up ChromaDB for vector storage")
    print("• Configure LangChain for LLM integration")

if __name__ == "__main__":
    main()