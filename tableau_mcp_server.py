#!/usr/bin/env python3
"""
Tableau MCP Server

A Model Context Protocol server that provides Claude Desktop with access to Tableau Server.
This server exposes Tableau workbooks, views, and data as MCP tools and resources.
"""

import asyncio
import os
import logging
import sys
import argparse
from typing import Any, Sequence, Dict, List, Optional
import io
import base64
import csv
import zipfile
import tempfile
import shutil
from dotenv import load_dotenv

# Import MCP components
from mcp.server.models import InitializationOptions
from mcp.server import NotificationOptions, Server
from mcp.server.stdio import stdio_server
from mcp.types import (
    Resource, Tool, TextContent, ImageContent, EmbeddedResource,
    LoggingLevel
)

# Import Tableau Server Client
import tableauserverclient as TSC

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("tableau-mcp")

class TableauMCPServer:
    """MCP Server for Tableau integration"""
    
    def __init__(self):
        self.server = Server("tableau-mcp")
        self.tableau_server = None
        self.tableau_auth = None
        self._authenticated = False
        
        # Setup server handlers
        self._setup_handlers()
        
    def _setup_handlers(self):
        """Setup MCP server request handlers"""
        
        @self.server.list_resources()
        async def handle_list_resources() -> list[Resource]:
            """List available Tableau resources"""
            resources = []
            
            if not await self._ensure_authenticated():
                return resources
                
            try:
                # Get all workbooks - but don't populate views here
                workbooks, _ = self.tableau_server.workbooks.get()
                
                for workbook in workbooks:
                    resources.append(Resource(
                        uri=f"tableau://workbooks/{workbook.id}",
                        name=f"Workbook: {workbook.name}",
                        description=f"Tableau workbook: {workbook.name}",
                        mimeType="application/json"
                    ))
                        
            except Exception as e:
                logger.error(f"Error listing resources: {e}")
                
            return resources
        
        @self.server.read_resource()
        async def handle_read_resource(uri: str) -> str:
            """Read a specific Tableau resource"""
            
            if not await self._ensure_authenticated():
                return "Error: Not authenticated with Tableau Server"
                
            try:
                if uri.startswith("tableau://workbooks/"):
                    workbook_id = uri.split("/")[-1]
                    return await self._get_workbook_metadata(workbook_id)
                    
                elif uri.startswith("tableau://views/") and uri.endswith("/data"):
                    view_id = uri.split("/")[-2]
                    return await self._get_view_data(view_id)
                    
                else:
                    return f"Error: Unknown resource URI: {uri}"
                    
            except Exception as e:
                logger.error(f"Error reading resource {uri}: {e}")
                return f"Error reading resource: {e}"
        
        @self.server.list_tools()
        async def handle_list_tools() -> list[Tool]:
            """List available Tableau tools"""
            return [
                Tool(
                    name="list_workbooks",
                    description="List all available Tableau workbooks",
                    inputSchema={
                        "type": "object",
                        "properties": {},
                        "required": []
                    }
                ),
                Tool(
                    name="list_views", 
                    description="List all views in a specific workbook",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "workbook_name": {
                                "type": "string",
                                "description": "Name of the workbook to list views for"
                            }
                        },
                        "required": ["workbook_name"]
                    }
                ),
                Tool(
                    name="get_view_data",
                    description="Get data from a specific Tableau view as CSV",
                    inputSchema={
                        "type": "object", 
                        "properties": {
                            "view_name": {
                                "type": "string",
                                "description": "Name of the view to get data from"
                            },
                            "workbook_name": {
                                "type": "string",
                                "description": "Name of the workbook containing the view (optional if view name is unique)"
                            }
                        },
                        "required": ["view_name"]
                    }
                ),
                Tool(
                    name="get_view_image",
                    description="Get an image of a Tableau view/dashboard",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "view_name": {
                                "type": "string", 
                                "description": "Name of the view to get image for"
                            },
                            "workbook_name": {
                                "type": "string",
                                "description": "Name of the workbook containing the view (optional)"
                            }
                        },
                        "required": ["view_name"]
                    }
                ),
                Tool(
                    name="search_content",
                    description="Search for Tableau content (workbooks, views) by name or description",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string",
                                "description": "Search query for finding Tableau content"
                            }
                        },
                        "required": ["query"]
                    }
                ),
                Tool(
                    name="list_datasources",
                    description="List all available Tableau data sources",
                    inputSchema={
                        "type": "object",
                        "properties": {},
                        "required": []
                    }
                ),
                Tool(
                    name="download_datasource",
                    description="Download complete dataset from a Tableau data source (gets ALL raw data)",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "datasource_name": {
                                "type": "string",
                                "description": "Name of the data source to download"
                            },
                            "include_extract": {
                                "type": "boolean",
                                "description": "Whether to include extract data (default: true)",
                                "default": True
                            }
                        },
                        "required": ["datasource_name"]
                    }
                ),
                Tool(
                    name="list_workbook_permissions",
                    description="List all users and groups with access to a specific workbook and their permission levels",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "workbook_name": {
                                "type": "string",
                                "description": "Name of the workbook to check permissions for"
                            }
                        },
                        "required": ["workbook_name"]
                    }
                ),
                Tool(
                    name="list_all_users",
                    description="List all users on the Tableau Server with their details",
                    inputSchema={
                        "type": "object",
                        "properties": {},
                        "required": []
                    }
                ),
                Tool(
                    name="list_all_groups",
                    description="List all groups on the Tableau Server with member counts",
                    inputSchema={
                        "type": "object",
                        "properties": {},
                        "required": []
                    }
                ),
                Tool(
                    name="get_user_permissions",
                    description="Get all permissions and access levels for a specific user",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "username": {
                                "type": "string",
                                "description": "Username to check permissions for"
                            }
                        },
                        "required": ["username"]
                    }
                ),
                Tool(
                    name="list_projects_permissions",
                    description="List all projects and their permission settings",
                    inputSchema={
                        "type": "object",
                        "properties": {},
                        "required": []
                    }
                ),
                Tool(
                    name="get_site_info",
                    description="Get Tableau Server site information and administrative details",
                    inputSchema={
                        "type": "object",
                        "properties": {},
                        "required": []
                    }
                ),
                Tool(
                    name="audit_workbook_usage",
                    description="Get usage statistics and access audit for a workbook",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "workbook_name": {
                                "type": "string",
                                "description": "Name of the workbook to audit"
                            }
                        },
                        "required": ["workbook_name"]
                    }
                ),
                Tool(
                    name="list_user_groups",
                    description="List all groups that a specific user belongs to",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "username": {
                                "type": "string",
                                "description": "Username to check group membership for"
                            }
                        },
                        "required": ["username"]
                    }
                )
            ]
        
        @self.server.list_prompts()
        async def handle_list_prompts() -> list:
            """Handle prompts list requests"""
            return []
        
        @self.server.call_tool()
        async def handle_call_tool(name: str, arguments: dict) -> list[TextContent | ImageContent]:
            """Handle tool calls"""
            
            if not await self._ensure_authenticated():
                return [TextContent(
                    type="text",
                    text="Error: Not authenticated with Tableau Server. Please check your credentials."
                )]
            
            try:
                if name == "list_workbooks":
                    return await self._handle_list_workbooks()
                    
                elif name == "list_views":
                    workbook_name = arguments.get("workbook_name")
                    return await self._handle_list_views(workbook_name)
                    
                elif name == "get_view_data":
                    view_name = arguments.get("view_name")
                    workbook_name = arguments.get("workbook_name")
                    return await self._handle_get_view_data(view_name, workbook_name)
                    
                elif name == "get_view_image":
                    view_name = arguments.get("view_name")
                    workbook_name = arguments.get("workbook_name")
                    return await self._handle_get_view_image(view_name, workbook_name)
                    
                elif name == "search_content":
                    query = arguments.get("query")
                    return await self._handle_search_content(query)
                    
                elif name == "list_datasources":
                    return await self._handle_list_datasources()
                    
                elif name == "download_datasource":
                    datasource_name = arguments.get("datasource_name")
                    include_extract = arguments.get("include_extract", True)
                    return await self._handle_download_datasource(datasource_name, include_extract)
                    
                elif name == "list_workbook_permissions":
                    workbook_name = arguments.get("workbook_name")
                    return await self._handle_list_workbook_permissions(workbook_name)
                    
                elif name == "list_all_users":
                    return await self._handle_list_all_users()
                    
                elif name == "list_all_groups":
                    return await self._handle_list_all_groups()
                    
                elif name == "get_user_permissions":
                    username = arguments.get("username")
                    return await self._handle_get_user_permissions(username)
                    
                elif name == "list_projects_permissions":
                    return await self._handle_list_projects_permissions()
                    
                elif name == "get_site_info":
                    return await self._handle_get_site_info()
                    
                elif name == "audit_workbook_usage":
                    workbook_name = arguments.get("workbook_name")
                    return await self._handle_audit_workbook_usage(workbook_name)
                    
                elif name == "list_user_groups":
                    username = arguments.get("username")
                    return await self._handle_list_user_groups(username)
                    
                else:
                    return [TextContent(
                        type="text",
                        text=f"Error: Unknown tool '{name}'"
                    )]
                    
            except Exception as e:
                logger.error(f"Error in tool {name}: {e}")
                return [TextContent(
                    type="text",
                    text=f"Error executing tool {name}: {e}"
                )]
    
    async def _ensure_authenticated(self) -> bool:
        """Ensure we're authenticated with Tableau Server"""
        if self._authenticated and self.tableau_server:
            return True
            
        try:
            # Get configuration from environment
            server_url = os.getenv('TABLEAU_SERVER_URL')
            site_id = os.getenv('TABLEAU_SITE_ID', '')
            
            if not server_url:
                logger.error("TABLEAU_SERVER_URL not set in environment")
                return False
                
            # Create server object
            self.tableau_server = TSC.Server(server_url, use_server_version=True)
            
            # Try token authentication first
            token_name = os.getenv('TABLEAU_TOKEN_NAME')
            token_value = os.getenv('TABLEAU_TOKEN_VALUE')
            
            if token_name and token_value:
                self.tableau_auth = TSC.PersonalAccessTokenAuth(
                    token_name, token_value, site_id
                )
            else:
                # Fall back to username/password
                username = os.getenv('TABLEAU_USERNAME')
                password = os.getenv('TABLEAU_PASSWORD')
                
                if not username or not password:
                    logger.error("No valid authentication credentials found")
                    return False
                    
                self.tableau_auth = TSC.TableauAuth(username, password, site_id)
            
            # Sign in
            self.tableau_server.auth.sign_in(self.tableau_auth)
            self._authenticated = True
            logger.info("Successfully authenticated with Tableau Server")
            return True
            
        except Exception as e:
            logger.error(f"Authentication failed: {e}")
            self._authenticated = False
            return False
    
    async def _handle_list_workbooks(self) -> list[TextContent]:
        """Handle list_workbooks tool call"""
        try:
            workbooks, pagination_item = self.tableau_server.workbooks.get()
            
            if not workbooks:
                return [TextContent(
                    type="text",
                    text="No workbooks found on the Tableau Server."
                )]
            
            workbook_info = []
            for wb in workbooks:
                info = f"• **{wb.name}**"
                if wb.description:
                    info += f" - {wb.description}"
                info += f" (ID: {wb.id}, Created: {wb.created_at})"
                workbook_info.append(info)
            
            result = "## Available Tableau Workbooks\n\n" + "\n".join(workbook_info)
            
            return [TextContent(type="text", text=result)]
            
        except Exception as e:
            raise Exception(f"Failed to list workbooks: {e}")
    
    async def _handle_list_views(self, workbook_name: str) -> list[TextContent]:
        """Handle list_views tool call"""
        try:
            # Find the workbook
            workbooks, _ = self.tableau_server.workbooks.get()
            target_workbook = None
            
            for wb in workbooks:
                if wb.name.lower() == workbook_name.lower():
                    target_workbook = wb
                    break
            
            if not target_workbook:
                return [TextContent(
                    type="text",
                    text=f"Workbook '{workbook_name}' not found."
                )]
            
            # Get views for the workbook
            self.tableau_server.workbooks.populate_views(target_workbook)
            
            if not target_workbook.views:
                return [TextContent(
                    type="text",
                    text=f"No views found in workbook '{workbook_name}'."
                )]
            
            view_info = []
            for view in target_workbook.views:
                info = f"• **{view.name}** (ID: {view.id})"
                if hasattr(view, 'content_url'):
                    info += f" - URL: {view.content_url}"
                view_info.append(info)
            
            result = f"## Views in Workbook '{workbook_name}'\n\n" + "\n".join(view_info)
            
            return [TextContent(type="text", text=result)]
            
        except Exception as e:
            raise Exception(f"Failed to list views: {e}")
    
    async def _handle_get_view_data(self, view_name: str, workbook_name: Optional[str] = None) -> list[TextContent]:
        """Handle get_view_data tool call"""
        try:
            # Find the view
            view = await self._find_view(view_name, workbook_name)
            if not view:
                return [TextContent(
                    type="text",
                    text=f"View '{view_name}' not found."
                )]
            
            # Get the view data
            self.tableau_server.views.populate_csv(view)
            csv_data = b''.join(view.csv).decode('utf-8')
            
            # Parse CSV to provide a summary
            csv_reader = csv.reader(io.StringIO(csv_data))
            rows = list(csv_reader)
            
            if not rows:
                return [TextContent(
                    type="text",
                    text=f"No data found in view '{view_name}'."
                )]
            
            headers = rows[0] if rows else []
            data_rows = rows[1:] if len(rows) > 1 else []
            
            summary = f"## Data from View '{view_name}'\n\n"
            summary += f"**Columns:** {', '.join(headers)}\n"
            summary += f"**Rows:** {len(data_rows)}\n\n"
            
            # Show first few rows as preview
            if data_rows:
                summary += "**Preview (first 5 rows):**\n\n"
                preview_rows = data_rows[:5]
                
                # Simple table format
                summary += "| " + " | ".join(headers) + " |\n"
                summary += "| " + " | ".join(["---"] * len(headers)) + " |\n"
                
                for row in preview_rows:
                    summary += "| " + " | ".join(str(cell) for cell in row) + " |\n"
                
                if len(data_rows) > 5:
                    summary += f"\n... and {len(data_rows) - 5} more rows.\n"
            
            summary += f"\n**Full CSV Data:**\n```csv\n{csv_data}\n```"
            
            return [TextContent(type="text", text=summary)]
            
        except Exception as e:
            raise Exception(f"Failed to get view data: {e}")
    
    async def _handle_get_view_image(self, view_name: str, workbook_name: Optional[str] = None) -> list[ImageContent]:
        """Handle get_view_image tool call"""
        try:
            # Find the view
            view = await self._find_view(view_name, workbook_name)
            if not view:
                return [TextContent(
                    type="text",
                    text=f"View '{view_name}' not found."
                )]
            
            # Get the view image
            self.tableau_server.views.populate_image(view)
            
            # Convert to base64
            image_base64 = base64.b64encode(view.image).decode('utf-8')
            
            return [ImageContent(
                type="image",
                data=image_base64,
                mimeType="image/png"
            )]
            
        except Exception as e:
            raise Exception(f"Failed to get view image: {e}")
    
    async def _handle_search_content(self, query: str) -> list[TextContent]:
        """Handle search_content tool call"""
        try:
            results = []
            
            # Search workbooks
            workbooks, _ = self.tableau_server.workbooks.get()
            matching_workbooks = []
            
            for wb in workbooks:
                if (query.lower() in wb.name.lower() or 
                    (wb.description and query.lower() in wb.description.lower())):
                    matching_workbooks.append(wb)
            
            # Search views
            matching_views = []
            for wb in matching_workbooks:
                try:
                    self.tableau_server.workbooks.populate_views(wb)
                    for view in wb.views:
                        if query.lower() in view.name.lower():
                            matching_views.append((view, wb.name))
                except:
                    continue
            
            result = f"## Search Results for '{query}'\n\n"
            
            if matching_workbooks:
                result += "### Matching Workbooks:\n"
                for wb in matching_workbooks:
                    result += f"• **{wb.name}**"
                    if wb.description:
                        result += f" - {wb.description}"
                    result += "\n"
                result += "\n"
            
            if matching_views:
                result += "### Matching Views:\n"
                for view, workbook_name in matching_views:
                    result += f"• **{view.name}** (in workbook: {workbook_name})\n"
                result += "\n"
            
            if not matching_workbooks and not matching_views:
                result += "No matching content found."
            
            return [TextContent(type="text", text=result)]
            
        except Exception as e:
            raise Exception(f"Failed to search content: {e}")

    async def _handle_list_datasources(self) -> list[TextContent]:
        """Handle list_datasources tool call"""
        try:
            datasources, _ = self.tableau_server.datasources.get()
            
            if not datasources:
                return [TextContent(
                    type="text",
                    text="No data sources found on the Tableau Server."
                )]
            
            datasource_info = []
            for ds in datasources:
                info = f"• **{ds.name}**"
                if ds.description:
                    info += f" - {ds.description}"
                info += f" (ID: {ds.id}, Project: {ds.project_name})"
                if hasattr(ds, 'size') and ds.size:
                    info += f" - Size: {ds.size} bytes"
                if hasattr(ds, 'content_url'):
                    info += f" - URL: {ds.content_url}"
                datasource_info.append(info)
            
            result = "## Available Tableau Data Sources\n\n" + "\n".join(datasource_info)
            result += f"\n\n**Total: {len(datasources)} data sources**"
            result += "\n\n💡 **Use `download_datasource` to get complete raw datasets!**"
            
            return [TextContent(type="text", text=result)]
            
        except Exception as e:
            raise Exception(f"Failed to list data sources: {e}")

    async def _handle_download_datasource(self, datasource_name: str, include_extract: bool = True) -> list[TextContent]:
        """Handle download_datasource tool call - gets COMPLETE raw dataset"""
        try:
            # Find the data source
            datasources, _ = self.tableau_server.datasources.get()
            target_datasource = None
            
            for ds in datasources:
                if ds.name.lower() == datasource_name.lower():
                    target_datasource = ds
                    break
            
            if not target_datasource:
                available_names = [ds.name for ds in datasources]
                return [TextContent(
                    type="text",
                    text=f"Data source '{datasource_name}' not found.\n\nAvailable data sources:\n" + 
                         "\n".join([f"• {name}" for name in available_names])
                )]
            
            # Download the data source
            logger.info(f"Downloading data source: {target_datasource.name}")
            
            # Create temporary directory
            with tempfile.TemporaryDirectory() as temp_dir:
                file_path = os.path.join(temp_dir, f"{target_datasource.name}.tdsx")
                
                # Download using the REST API
                with open(file_path, 'wb') as f:
                    self.tableau_server.datasources.download(target_datasource.id, f, include_extract=include_extract)
                
                logger.info(f"Downloaded data source to: {file_path}")
                
                # Analyze the downloaded file
                file_size = os.path.getsize(file_path)
                
                result = f"## Downloaded Complete Dataset: '{target_datasource.name}'\n\n"
                result += f"**File Size:** {file_size:,} bytes ({file_size/1024/1024:.1f} MB)\n"
                result += f"**Format:** .tdsx (Tableau Data Source with Extract)\n"
                result += f"**Include Extract:** {include_extract}\n\n"
                
                # Try to extract and analyze the contents
                try:
                    with zipfile.ZipFile(file_path, 'r') as zip_ref:
                        file_list = zip_ref.namelist()
                        result += f"**Archive Contents:** {len(file_list)} files\n"
                        
                        # Look for data files
                        data_files = [f for f in file_list if f.endswith(('.csv', '.hyper', '.tde'))]
                        if data_files:
                            result += f"**Data Files Found:** {len(data_files)}\n"
                            for df in data_files[:5]:  # Show first 5
                                file_info = zip_ref.getinfo(df)
                                result += f"  • {df} ({file_info.file_size:,} bytes)\n"
                            if len(data_files) > 5:
                                result += f"  • ... and {len(data_files) - 5} more data files\n"
                        
                        # Look for .tds file (connection info)
                        tds_files = [f for f in file_list if f.endswith('.tds')]
                        if tds_files:
                            result += f"**Connection Files:** {len(tds_files)}\n"
                            
                            # Try to read the .tds file for schema info
                            for tds_file in tds_files[:1]:  # Just the first one
                                try:
                                    tds_content = zip_ref.read(tds_file).decode('utf-8')
                                    if 'column' in tds_content.lower():
                                        # Count columns mentioned in the file
                                        column_count = tds_content.lower().count('<column')
                                        if column_count > 0:
                                            result += f"**Estimated Columns:** ~{column_count}\n"
                                except:
                                    pass
                        
                        # Check for Hyper files (Tableau's fast data format)
                        hyper_files = [f for f in file_list if f.endswith('.hyper')]
                        if hyper_files:
                            result += f"**Hyper Extract Files:** {len(hyper_files)}\n"
                            for hf in hyper_files:
                                file_info = zip_ref.getinfo(hf)
                                result += f"  • {hf} ({file_info.file_size:,} bytes)\n"
                
                except Exception as e:
                    result += f"**Note:** Could not analyze archive contents: {e}\n"
                
                result += "\n🎉 **SUCCESS! Complete dataset downloaded!**\n\n"
                result += "📊 **What you now have:**\n"
                result += "• **ALL rows and columns** from the original data source\n"
                result += "• **Raw data** before any filtering or aggregation\n"
                result += "• **Multiple tables** if the data source contains them\n"
                result += "• **Complete data structure** and relationships\n\n"
                result += "💡 **Next steps:**\n"
                result += "• This data is ready for comprehensive analysis\n"
                result += "• Ask Claude to analyze patterns, trends, or specific insights\n"
                result += "• The complete dataset provides much richer analysis than view-level data\n"
                
                return [TextContent(type="text", text=result)]
                
        except Exception as e:
            logger.error(f"Error downloading data source: {e}")
            return [TextContent(
                type="text",
                text=f"Error downloading data source '{datasource_name}': {e}\n\n"
                     "Make sure you have the proper permissions to download data sources."
            )]
    
    async def _find_view(self, view_name: str, workbook_name: Optional[str] = None) -> Optional[Any]:
        """Find a view by name, optionally within a specific workbook"""
        workbooks, _ = self.tableau_server.workbooks.get()
        
        target_workbooks = []
        if workbook_name:
            # Search in specific workbook
            for wb in workbooks:
                if wb.name.lower() == workbook_name.lower():
                    target_workbooks = [wb]
                    break
        else:
            # Search in all workbooks
            target_workbooks = workbooks
        
        for wb in target_workbooks:
            try:
                self.tableau_server.workbooks.populate_views(wb)
                for view in wb.views:
                    if view.name.lower() == view_name.lower():
                        return view
            except Exception as e:
                logger.warning(f"Could not get views for workbook {wb.name}: {e}")
                continue
        
        return None
    
    async def _get_workbook_metadata(self, workbook_id: str) -> str:
        """Get metadata for a specific workbook"""
        try:
            workbook = self.tableau_server.workbooks.get_by_id(workbook_id)
            self.tableau_server.workbooks.populate_views(workbook)
            
            metadata = {
                "id": workbook.id,
                "name": workbook.name,
                "description": workbook.description,
                "created_at": str(workbook.created_at),
                "updated_at": str(workbook.updated_at),
                "project_name": workbook.project_name,
                "owner_id": workbook.owner_id,
                "size": workbook.size,
                "views": [{"id": view.id, "name": view.name} for view in workbook.views]
            }
            
            return str(metadata)
            
        except Exception as e:
            return f"Error getting workbook metadata: {e}"
    
    async def _get_view_data(self, view_id: str) -> str:
        """Get CSV data for a specific view"""
        try:
            view = self.tableau_server.views.get_by_id(view_id)
            self.tableau_server.views.populate_csv(view)
            
            return b''.join(view.csv).decode('utf-8')
            
        except Exception as e:
            return f"Error getting view data: {e}"
    
    async def _handle_list_workbook_permissions(self, workbook_name: str) -> list[TextContent]:
        """Handle list_workbook_permissions tool call"""
        try:
            # Find the workbook
            workbooks, _ = self.tableau_server.workbooks.get()
            target_workbook = None
            
            for wb in workbooks:
                if wb.name.lower() == workbook_name.lower():
                    target_workbook = wb
                    break
            
            if not target_workbook:
                return [TextContent(
                    type="text",
                    text=f"Workbook '{workbook_name}' not found."
                )]
            
            # Get permissions for the workbook
            self.tableau_server.workbooks.populate_permissions(target_workbook)
            
            result = f"## Permissions for Workbook '{workbook_name}'\n\n"
            
            if not target_workbook.permissions:
                result += "No explicit permissions set (inherits from project).\n"
            else:
                # Group permissions by capability
                user_permissions = {}
                group_permissions = {}
                
                for permission in target_workbook.permissions:
                    capability_name = permission.capability.name
                    mode = permission.mode.name
                    
                    if permission.grantee.tag_name == 'user':
                        user_id = permission.grantee.id
                        if user_id not in user_permissions:
                            user_permissions[user_id] = {}
                        user_permissions[user_id][capability_name] = mode
                    elif permission.grantee.tag_name == 'group':
                        group_id = permission.grantee.id
                        if group_id not in group_permissions:
                            group_permissions[group_id] = {}
                        group_permissions[group_id][capability_name] = mode
                
                # Get user details
                if user_permissions:
                    result += "### 👤 User Permissions:\n"
                    users, _ = self.tableau_server.users.get()
                    user_lookup = {user.id: user for user in users}
                    
                    for user_id, capabilities in user_permissions.items():
                        user = user_lookup.get(user_id)
                        username = user.name if user else f"User ID: {user_id}"
                        result += f"\n**{username}**\n"
                        for capability, mode in capabilities.items():
                            result += f"  • {capability}: {mode}\n"
                    result += "\n"
                
                # Get group details
                if group_permissions:
                    result += "### 👥 Group Permissions:\n"
                    groups, _ = self.tableau_server.groups.get()
                    group_lookup = {group.id: group for group in groups}
                    
                    for group_id, capabilities in group_permissions.items():
                        group = group_lookup.get(group_id)
                        groupname = group.name if group else f"Group ID: {group_id}"
                        result += f"\n**{groupname}**\n"
                        for capability, mode in capabilities.items():
                            result += f"  • {capability}: {mode}\n"
                    result += "\n"
            
            # Add project information
            result += f"### 📁 Project Information:\n"
            result += f"**Project:** {target_workbook.project_name}\n"
            result += f"**Owner:** {target_workbook.owner_id}\n"
            
            return [TextContent(type="text", text=result)]
            
        except Exception as e:
            raise Exception(f"Failed to get workbook permissions: {e}")

    async def _handle_list_all_users(self) -> list[TextContent]:
        """Handle list_all_users tool call"""
        try:
            users, _ = self.tableau_server.users.get()
            
            if not users:
                return [TextContent(
                    type="text",
                    text="No users found on the Tableau Server."
                )]
            
            result = f"## All Tableau Server Users ({len(users)} total)\n\n"
            
            # Group users by site role
            role_groups = {}
            for user in users:
                role = user.site_role
                if role not in role_groups:
                    role_groups[role] = []
                role_groups[role].append(user)
            
            for role, role_users in role_groups.items():
                result += f"### 🔰 {role.title()} ({len(role_users)} users):\n"
                for user in role_users:
                    result += f"• **{user.name}**"
                    if user.fullname:
                        result += f" ({user.fullname})"
                    result += f" - Last Login: {user.last_login or 'Never'}\n"
                result += "\n"
            
            return [TextContent(type="text", text=result)]
            
        except Exception as e:
            raise Exception(f"Failed to list users: {e}")

    async def _handle_list_all_groups(self) -> list[TextContent]:
        """Handle list_all_groups tool call"""
        try:
            groups, _ = self.tableau_server.groups.get()
            
            if not groups:
                return [TextContent(
                    type="text",
                    text="No groups found on the Tableau Server."
                )]
            
            result = f"## All Tableau Server Groups ({len(groups)} total)\n\n"
            
            for group in groups:
                result += f"• **{group.name}**"
                if group.domain_name:
                    result += f" (Domain: {group.domain_name})"
                
                # Try to get member count
                try:
                    self.tableau_server.groups.populate_users(group)
                    member_count = len(group.users) if group.users else 0
                    result += f" - {member_count} members"
                except:
                    result += " - Member count unavailable"
                
                result += "\n"
            
            return [TextContent(type="text", text=result)]
            
        except Exception as e:
            raise Exception(f"Failed to list groups: {e}")

    async def _handle_get_user_permissions(self, username: str) -> list[TextContent]:
        """Handle get_user_permissions tool call"""
        try:
            # Find the user
            users, _ = self.tableau_server.users.get()
            target_user = None
            
            for user in users:
                if user.name.lower() == username.lower():
                    target_user = user
                    break
            
            if not target_user:
                return [TextContent(
                    type="text",
                    text=f"User '{username}' not found."
                )]
            
            result = f"## Permissions for User '{target_user.name}'\n\n"
            result += f"**Full Name:** {target_user.fullname or 'Not specified'}\n"
            result += f"**Site Role:** {target_user.site_role}\n"
            result += f"**Last Login:** {target_user.last_login or 'Never'}\n\n"
            
            # Get workbooks this user owns
            workbooks, _ = self.tableau_server.workbooks.get()
            owned_workbooks = [wb for wb in workbooks if wb.owner_id == target_user.id]
            
            if owned_workbooks:
                result += f"### 📊 Owned Workbooks ({len(owned_workbooks)}):\n"
                for wb in owned_workbooks:
                    result += f"• {wb.name}\n"
                result += "\n"
            
            # Get groups this user belongs to
            try:
                groups, _ = self.tableau_server.groups.get()
                user_groups = []
                for group in groups:
                    try:
                        self.tableau_server.groups.populate_users(group)
                        if any(u.id == target_user.id for u in group.users):
                            user_groups.append(group.name)
                    except:
                        continue
                
                if user_groups:
                    result += f"### 👥 Group Memberships ({len(user_groups)}):\n"
                    for group_name in user_groups:
                        result += f"• {group_name}\n"
                    result += "\n"
            except Exception as e:
                result += f"### 👥 Group Memberships: Could not retrieve ({e})\n\n"
            
            return [TextContent(type="text", text=result)]
            
        except Exception as e:
            raise Exception(f"Failed to get user permissions: {e}")

    async def _handle_list_projects_permissions(self) -> list[TextContent]:
        """Handle list_projects_permissions tool call"""
        try:
            projects, _ = self.tableau_server.projects.get()
            
            if not projects:
                return [TextContent(
                    type="text",
                    text="No projects found on the Tableau Server."
                )]
            
            result = f"## All Projects and Permissions ({len(projects)} total)\n\n"
            
            for project in projects:
                result += f"### 📁 {project.name}\n"
                result += f"**Description:** {project.description or 'No description'}\n"
                result += f"**Content Permissions:** {project.content_permissions_mode}\n"
                
                # Count workbooks in project
                workbooks, _ = self.tableau_server.workbooks.get()
                project_workbooks = [wb for wb in workbooks if wb.project_name == project.name]
                result += f"**Workbooks:** {len(project_workbooks)}\n"
                
                # Get project permissions
                try:
                    self.tableau_server.projects.populate_permissions(project)
                    if project.permissions:
                        result += f"**Explicit Permissions:** {len(project.permissions)} rules\n"
                    else:
                        result += "**Permissions:** Inherited from parent\n"
                except:
                    result += "**Permissions:** Could not retrieve\n"
                
                result += "\n"
            
            return [TextContent(type="text", text=result)]
            
        except Exception as e:
            raise Exception(f"Failed to list projects: {e}")

    async def _handle_get_site_info(self) -> list[TextContent]:
        """Handle get_site_info tool call"""
        try:
            # Get current site info
            site = self.tableau_server.sites.get_by_id(self.tableau_server.site_id)
            
            result = "## Tableau Server Site Information\n\n"
            result += f"**Site Name:** {site.name}\n"
            result += f"**Site ID:** {site.id}\n"
            result += f"**Content URL:** {site.content_url or 'Default site'}\n"
            result += f"**Admin Mode:** {site.admin_mode}\n"
            result += f"**State:** {site.state}\n"
            result += f"**Storage Quota:** {site.storage_quota or 'Unlimited'}\n"
            result += f"**User Quota:** {site.user_quota or 'Unlimited'}\n\n"
            
            # Get counts
            users, _ = self.tableau_server.users.get()
            workbooks, _ = self.tableau_server.workbooks.get()
            datasources, _ = self.tableau_server.datasources.get()
            projects, _ = self.tableau_server.projects.get()
            groups, _ = self.tableau_server.groups.get()
            
            result += "### 📊 Content Summary:\n"
            result += f"• **Users:** {len(users)}\n"
            result += f"• **Groups:** {len(groups)}\n"
            result += f"• **Projects:** {len(projects)}\n"
            result += f"• **Workbooks:** {len(workbooks)}\n"
            result += f"• **Data Sources:** {len(datasources)}\n\n"
            
            # User role breakdown
            role_counts = {}
            for user in users:
                role = user.site_role
                role_counts[role] = role_counts.get(role, 0) + 1
            
            result += "### 👤 User Roles:\n"
            for role, count in role_counts.items():
                result += f"• **{role.title()}:** {count}\n"
            
            return [TextContent(type="text", text=result)]
            
        except Exception as e:
            raise Exception(f"Failed to get site info: {e}")

    async def _handle_audit_workbook_usage(self, workbook_name: str) -> list[TextContent]:
        """Handle audit_workbook_usage tool call"""
        try:
            # Find the workbook
            workbooks, _ = self.tableau_server.workbooks.get()
            target_workbook = None
            
            for wb in workbooks:
                if wb.name.lower() == workbook_name.lower():
                    target_workbook = wb
                    break
            
            if not target_workbook:
                return [TextContent(
                    type="text",
                    text=f"Workbook '{workbook_name}' not found."
                )]
            
            result = f"## Usage Audit for Workbook '{workbook_name}'\n\n"
            
            # Basic workbook info
            result += f"**Created:** {target_workbook.created_at}\n"
            result += f"**Updated:** {target_workbook.updated_at}\n"
            result += f"**Size:** {target_workbook.size or 'Unknown'} bytes\n"
            result += f"**Project:** {target_workbook.project_name}\n\n"
            
            # Get views
            self.tableau_server.workbooks.populate_views(target_workbook)
            if target_workbook.views:
                result += f"### 📈 Views ({len(target_workbook.views)}):\n"
                for view in target_workbook.views:
                    result += f"• **{view.name}** (ID: {view.id})\n"
                result += "\n"
            
            # Get permissions (who can access)
            try:
                self.tableau_server.workbooks.populate_permissions(target_workbook)
                if target_workbook.permissions:
                    result += f"### 🔐 Access Control:\n"
                    result += f"**Explicit Permissions:** {len(target_workbook.permissions)} rules\n"
                    
                    # Count users vs groups
                    user_perms = sum(1 for p in target_workbook.permissions if p.grantee.tag_name == 'user')
                    group_perms = sum(1 for p in target_workbook.permissions if p.grantee.tag_name == 'group')
                    
                    result += f"**Direct User Access:** {user_perms} users\n"
                    result += f"**Group-based Access:** {group_perms} groups\n"
                else:
                    result += "### 🔐 Access Control:\nInherits permissions from project\n"
            except Exception as e:
                result += f"### 🔐 Access Control:\nCould not retrieve permissions: {e}\n"
            
            result += "\n💡 **Recommendation:** Use the `list_workbook_permissions` tool for detailed access information."
            
            return [TextContent(type="text", text=result)]
            
        except Exception as e:
            raise Exception(f"Failed to audit workbook usage: {e}")

    async def _handle_list_user_groups(self, username: str) -> list[TextContent]:
        """Handle list_user_groups tool call"""
        try:
            # Find the user
            users, _ = self.tableau_server.users.get()
            target_user = None
            
            for user in users:
                if user.name.lower() == username.lower():
                    target_user = user
                    break
            
            if not target_user:
                return [TextContent(
                    type="text",
                    text=f"User '{username}' not found."
                )]
            
            result = f"## Group Memberships for '{target_user.name}'\n\n"
            
            # Get all groups and check membership
            groups, _ = self.tableau_server.groups.get()
            user_groups = []
            
            for group in groups:
                try:
                    self.tableau_server.groups.populate_users(group)
                    if any(u.id == target_user.id for u in group.users):
                        user_groups.append(group)
                except:
                    continue
            
            if user_groups:
                result += f"**Total Groups:** {len(user_groups)}\n\n"
                for group in user_groups:
                    result += f"• **{group.name}**"
                    if group.domain_name:
                        result += f" (Domain: {group.domain_name})"
                    
                    # Show other members count
                    try:
                        other_members = len([u for u in group.users if u.id != target_user.id])
                        result += f" - {other_members} other members"
                    except:
                        pass
                    result += "\n"
            else:
                result += "User is not a member of any groups.\n"
            
            return [TextContent(type="text", text=result)]
            
        except Exception as e:
            raise Exception(f"Failed to list user groups: {e}")
    
    async def run(self):
        """Run the MCP server"""
        async with stdio_server() as (read_stream, write_stream):
            await self.server.run(
                read_stream,
                write_stream,
                InitializationOptions(
                    server_name="tableau-mcp",
                    server_version="1.0.0",
                    capabilities=self.server.get_capabilities(
                        notification_options=NotificationOptions(),
                        experimental_capabilities={}
                    )
                )
            )

def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description="Tableau MCP Server")
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")
    parser.add_argument("--test", action="store_true", help="Test authentication only")
    
    args = parser.parse_args()
    
    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)
        logger.setLevel(logging.DEBUG)
    
    if args.test:
        # Test authentication
        server = TableauMCPServer()
        async def test_auth():
            success = await server._ensure_authenticated()
            if success:
                print("✅ Authentication successful!")
                # Test basic functionality
                workbooks, _ = server.tableau_server.workbooks.get()
                print(f"📊 Found {len(workbooks)} workbooks")
                for wb in workbooks[:3]:  # Show first 3
                    print(f"  - {wb.name}")
            else:
                print("❌ Authentication failed!")
                sys.exit(1)
        
        asyncio.run(test_auth())
        return
    
    # Run the MCP server
    server = TableauMCPServer()
    asyncio.run(server.run())

if __name__ == "__main__":
    main() 