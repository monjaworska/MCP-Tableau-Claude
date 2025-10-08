# Tableau MCP Server 🚀

A powerful Model Context Protocol (MCP) server that connects Claude Desktop to Tableau Server, enabling natural language interactions with your Tableau data and comprehensive administrative capabilities.

## ✨ Features

### 📊 **Data Access & Analysis**
- **List & Browse**: Explore all workbooks, views, and data sources
- **Data Extraction**: Get CSV data from any Tableau view
- **Visual Export**: Download dashboard images in PNG format
- **Complete Datasets**: Download entire data sources with all raw data
- **Smart Search**: Find content across your Tableau server

### 🛡️ **Administrative Tools** (New!)
- **User Management**: List all users with roles and login history
- **Permission Auditing**: See exactly who has access to workbooks
- **Group Management**: View all groups and member counts
- **Project Oversight**: Audit project permissions and settings
- **Site Administration**: Get comprehensive site statistics
- **Usage Analytics**: Detailed workbook usage and access audits

## 🎯 **Use Cases**

### For Data Analysts
- "Show me the sales data from Q4 dashboard"
- "Export the customer metrics as CSV"
- "Find all reports containing revenue data"

### For Tableau Administrators
- "Who has access to the Finance workbook?"
- "List all users who haven't logged in recently"
- "Show me all groups and their member counts"
- "Audit the permissions for our HR dashboards"

## 🚀 **Quick Start**

### Prerequisites
- Python 3.8+
- Claude Desktop installed
- Access to Tableau Server or Tableau Cloud
- Administrative privileges (for admin tools)

### 1. Clone and Setup

```bash
# Clone the repository
git clone https://github.com/monjaworska/Tableau-MCP.git
cd Tableau-MCP

# Create virtual environment (recommended)
python -m venv tableau_mcp_env
source tableau_mcp_env/bin/activate  # On Windows: tableau_mcp_env\Scripts\activate

# Install ALL dependencies including MCP SDK
pip install -r requirements.txt
```

### 2. MCP SDK Installation (If Having Issues)

If you encounter MCP SDK installation issues, try these solutions:

```bash
# Option 1: Install MCP SDK directly
pip install mcp>=1.0.0

# Option 2: Install with specific version
pip install mcp==1.0.0

# Option 3: Install from source (if needed)
pip install git+https://github.com/modelcontextprotocol/python-sdk.git

# Option 4: Force reinstall
pip install --force-reinstall mcp>=1.0.0
```

### 3. Verify Installation

```bash
# Test that MCP SDK is properly installed
python -c "import mcp; print('✅ MCP SDK installed successfully')"

# Test Tableau Server Client
python -c "import tableauserverclient as TSC; print('✅ Tableau Server Client ready')"

# Test the server
python tableau_mcp_server.py --test
```

### 4. Configuration

Create a `.env` file with your Tableau credentials:

```env
TABLEAU_SERVER_URL=https://your-tableau-server.com
TABLEAU_SITE_ID=your-site-name

# Option 1: Personal Access Token (Recommended)
TABLEAU_TOKEN_NAME=your-token-name
TABLEAU_TOKEN_VALUE=your-token-value

# Option 2: Username/Password
# TABLEAU_USERNAME=your-username
# TABLEAU_PASSWORD=your-password
```

### 5. Claude Desktop Setup

Add to your Claude Desktop configuration:

**macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`

```json
{
  "mcpServers": {
    "tableau-server": {
      "command": "/path/to/Tableau-MCP/start_clean.sh",
      "args": []
    }
  }
}
```

### 6. Start the Server

```bash
# Make startup script executable
chmod +x start_clean.sh

# Start the server
./start_clean.sh
```

## 🛠️ **Available Tools**

### Data Access Tools
| Tool | Description |
|------|-------------|
| `list_workbooks` | List all available Tableau workbooks |
| `list_views` | List views in a specific workbook |
| `get_view_data` | Extract CSV data from any view |
| `get_view_image` | Get dashboard/view as PNG image |
| `search_content` | Search across all Tableau content |
| `list_datasources` | List all available data sources |
| `download_datasource` | Download complete raw datasets |

### Administrative Tools
| Tool | Description |
|------|-------------|
| `list_workbook_permissions` | See who has access to workbooks |
| `list_all_users` | View all users with roles and details |
| `list_all_groups` | View all groups with member counts |
| `get_user_permissions` | Get detailed user permissions |
| `list_projects_permissions` | Audit project permissions |
| `get_site_info` | Get site statistics and quotas |
| `audit_workbook_usage` | Comprehensive workbook audits |
| `list_user_groups` | See user group memberships |

## 📋 **MCP Resources**

The server exposes Tableau content as MCP resources:

- `tableau://workbooks/{workbook_id}` - Workbook metadata
- `tableau://views/{view_id}/data` - View data in CSV format

## 🔧 **Advanced Usage**

### Debug Mode
```bash
python tableau_mcp_server.py --debug
```

### Authentication Testing
```bash
python tableau_mcp_server.py --test
```

### Manual Setup
```bash
python setup.py --test-only
```

## 🏗️ **Architecture**

```
Claude Desktop ↔ MCP Server ↔ Tableau REST API ↔ Tableau Server
                     ⬇️
               [15 Available Tools]
                     ⬇️
            [Data + Admin Capabilities]
```

## 📁 **Project Structure**

```
Tableau-MCP/
├── tableau_mcp_server.py    # Main MCP server implementation
├── start_clean.sh           # Server startup script
├── requirements.txt         # Python dependencies (includes MCP SDK)
├── setup.py                # Setup and configuration script
├── env.example             # Environment configuration template
├── README.md               # This file
└── .env                    # Your credentials (create this)
```

## 🔒 **Security**

- **Local Operation**: Server runs locally with your permissions
- **Secure Credentials**: Uses environment variables for authentication
- **Token Authentication**: Supports Tableau Personal Access Tokens
- **No Data Leakage**: No data sent to external services

## 🚨 **Troubleshooting**

### MCP SDK Issues

**"ModuleNotFoundError: No module named 'mcp'"**
```bash
# Solution 1: Install MCP SDK
pip install mcp>=1.0.0

# Solution 2: Check virtual environment
source tableau_mcp_env/bin/activate
pip install -r requirements.txt

# Solution 3: Verify Python version
python --version  # Should be 3.8+
```

**"MCP SDK version conflict"**
```bash
# Uninstall and reinstall
pip uninstall mcp
pip install mcp>=1.0.0
```

### Common Issues

**"Authentication failed"**
- Verify credentials in `.env` file
- Check Tableau Server URL format
- Ensure account has proper permissions

**"No tools available in Claude"**
- Restart Claude Desktop after configuration
- Check that `start_clean.sh` is executable
- Verify Python dependencies are installed

**"Permission denied errors"**
- Ensure your account has administrative privileges
- Check Tableau Server user permissions
- Verify site access rights

### Getting Help

1. **Test Connection**: `python tableau_mcp_server.py --test`
2. **Debug Mode**: `python tableau_mcp_server.py --debug`
3. **Check Logs**: Look for error messages in terminal output
4. **Verify MCP**: `python -c "import mcp; print('MCP SDK OK')"`

## 📈 **Example Conversations**

### Data Analysis
```
User: "Show me all workbooks and find the sales data"
Claude: [Lists workbooks] → [Finds sales-related content] → [Extracts data]

User: "Get the customer metrics from the Q4 dashboard as CSV"
Claude: [Locates dashboard] → [Extracts view data] → [Provides CSV]
```

### Administration
```
User: "Who has access to our Finance workbook?"
Claude: [Lists all users and groups with permissions] → [Shows permission levels]

User: "Show me all users who are site administrators"
Claude: [Lists users by role] → [Highlights administrators]
```

## 🤝 **Contributing**

1. Fork the repository
2. Create a feature branch
3. Add your improvements
4. Test thoroughly
5. Submit a pull request

## 📄 **License**

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 **Acknowledgments**

- Built with the [Model Context Protocol](https://github.com/modelcontextprotocol)
- Uses [Tableau Server Client](https://github.com/tableau/server-client-python)
- Designed for [Claude Desktop](https://claude.ai/desktop)

---

**Ready to supercharge your Tableau workflows with Claude? Get started now!** 🎉 
