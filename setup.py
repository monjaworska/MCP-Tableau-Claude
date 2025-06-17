#!/usr/bin/env python3
"""
Setup script for Tableau MCP Server
"""

import os
import sys
import subprocess
import argparse

def check_python_version():
    """Check if Python version is 3.8+"""
    if sys.version_info < (3, 8):
        print("❌ Python 3.8 or higher is required")
        sys.exit(1)
    print(f"✅ Python {sys.version.split()[0]} detected")

def install_dependencies():
    """Install required dependencies"""
    print("📦 Installing dependencies...")
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])
        print("✅ Dependencies installed successfully")
    except subprocess.CalledProcessError:
        print("❌ Failed to install dependencies")
        sys.exit(1)

def create_env_file():
    """Create .env file from template"""
    env_example = """# Tableau Server Configuration
TABLEAU_SERVER_URL=https://your-tableau-server.com
TABLEAU_SITE_ID=your-site-name

# Authentication Method 1: Personal Access Token (Recommended)
TABLEAU_TOKEN_NAME=your-token-name
TABLEAU_TOKEN_VALUE=your-token-value

# Authentication Method 2: Username/Password (Alternative)
# TABLEAU_USERNAME=your-username
# TABLEAU_PASSWORD=your-password

# Optional: Additional configuration
# TABLEAU_API_VERSION=3.19
"""
    
    if not os.path.exists('.env'):
        with open('.env', 'w') as f:
            f.write(env_example)
        print("✅ Created .env file - please edit it with your Tableau credentials")
    else:
        print("ℹ️  .env file already exists")

def generate_claude_config():
    """Generate Claude Desktop configuration"""
    current_dir = os.path.abspath(os.path.dirname(__file__))
    
    config = f"""{{
  "mcpServers": {{
    "tableau": {{
      "command": "python",
      "args": ["{os.path.join(current_dir, 'tableau_mcp_server.py')}"],
      "cwd": "{current_dir}"
    }}
  }}
}}"""
    
    print("\n📋 Claude Desktop Configuration:")
    print("Add this to your claude_desktop_config.json file:")
    print("=" * 50)
    print(config)
    print("=" * 50)
    
    # Platform-specific configuration file locations
    if sys.platform == "darwin":  # macOS
        config_path = "~/Library/Application Support/Claude/claude_desktop_config.json"
    elif sys.platform == "win32":  # Windows
        config_path = "%APPDATA%\\Claude\\claude_desktop_config.json"
    else:  # Linux
        config_path = "~/.config/claude/claude_desktop_config.json"
    
    print(f"\n📍 Configuration file location: {config_path}")

def test_setup():
    """Test the Tableau connection"""
    print("\n🧪 Testing Tableau connection...")
    try:
        result = subprocess.run([sys.executable, "tableau_mcp_server.py", "--test"], 
                              capture_output=True, text=True)
        if result.returncode == 0:
            print("✅ Setup test completed successfully!")
            print(result.stdout)
        else:
            print("❌ Setup test failed:")
            print(result.stderr)
            print("\nPlease check your .env file configuration")
    except Exception as e:
        print(f"❌ Error running test: {e}")

def main():
    parser = argparse.ArgumentParser(description="Setup Tableau MCP Server")
    parser.add_argument("--test-only", action="store_true", help="Only run the connection test")
    parser.add_argument("--skip-install", action="store_true", help="Skip dependency installation")
    
    args = parser.parse_args()
    
    print("🚀 Tableau MCP Server Setup")
    print("=" * 30)
    
    if args.test_only:
        test_setup()
        return
    
    # Setup steps
    check_python_version()
    
    if not args.skip_install:
        install_dependencies()
    
    create_env_file()
    generate_claude_config()
    
    print("\n📝 Next Steps:")
    print("1. Edit the .env file with your Tableau Server credentials")
    print("2. Add the configuration to your Claude Desktop config file")
    print("3. Restart Claude Desktop")
    print("4. Test with: python setup.py --test-only")
    
    print("\n💡 Helpful Commands:")
    print("  python tableau_mcp_server.py --test     # Test connection")
    print("  python tableau_mcp_server.py --debug    # Run with debug logging")
    print("  python tableau_mcp_server.py            # Run the MCP server")

if __name__ == "__main__":
    main() 