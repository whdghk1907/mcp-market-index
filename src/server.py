"""
MCP Market Index Server Main Entry Point
"""
import asyncio
import logging
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

from .config import get_settings
from .utils.logger import setup_logger
from .utils.cache import MarketDataCache
from .api.client import KoreaInvestmentAPI

# Initialize settings
settings = get_settings()

# Setup logging
logger = setup_logger(__name__, settings.log_level)

# Initialize global components
cache = MarketDataCache()
api_client = KoreaInvestmentAPI(
    app_key=settings.korea_investment_app_key,
    app_secret=settings.korea_investment_app_secret
)

# Create MCP server instance
server = Server(settings.server_name)


@server.list_tools()
async def list_tools() -> list[Tool]:
    """List available tools"""
    return [
        Tool(
            name="get_market_index",
            description="현재 시장 지수 조회 (코스피/코스닥)",
            inputSchema={
                "type": "object",
                "properties": {
                    "market": {
                        "type": "string",
                        "enum": ["KOSPI", "KOSDAQ", "ALL"],
                        "default": "ALL",
                        "description": "조회할 시장"
                    }
                }
            }
        ),
        Tool(
            name="get_index_chart",
            description="지수 차트 데이터 조회",
            inputSchema={
                "type": "object",
                "properties": {
                    "market": {
                        "type": "string", 
                        "enum": ["KOSPI", "KOSDAQ"],
                        "description": "시장 구분"
                    },
                    "period": {
                        "type": "string",
                        "enum": ["1D", "1W", "1M", "3M", "1Y"],
                        "default": "1D",
                        "description": "조회 기간"
                    },
                    "interval": {
                        "type": "string",
                        "enum": ["1m", "5m", "30m", "1h", "1d"],
                        "default": "5m", 
                        "description": "데이터 간격"
                    }
                },
                "required": ["market"]
            }
        ),
        Tool(
            name="get_market_summary",
            description="시장 전체 요약 정보 조회",
            inputSchema={
                "type": "object",
                "properties": {}
            }
        ),
        Tool(
            name="get_sector_indices",
            description="업종별 지수 조회",
            inputSchema={
                "type": "object",
                "properties": {
                    "market": {
                        "type": "string",
                        "enum": ["KOSPI", "KOSDAQ"],
                        "default": "KOSPI",
                        "description": "시장 구분"
                    }
                }
            }
        ),
        Tool(
            name="get_market_compare",
            description="시장 지수 비교 (기간별 변화)",
            inputSchema={
                "type": "object",
                "properties": {
                    "date_from": {
                        "type": "string",
                        "pattern": "^\\d{4}-\\d{2}-\\d{2}$",
                        "description": "시작일 (YYYY-MM-DD)"
                    },
                    "date_to": {
                        "type": "string", 
                        "pattern": "^\\d{4}-\\d{2}-\\d{2}$",
                        "description": "종료일 (YYYY-MM-DD)"
                    }
                }
            }
        )
    ]


@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    """Handle tool calls"""
    try:
        logger.info(f"Tool called: {name} with arguments: {arguments}")
        
        if name == "get_market_index":
            from .tools.index_tools import get_market_index
            result = await get_market_index(
                market=arguments.get("market", "ALL"),
                cache=cache,
                api_client=api_client
            )
            
        elif name == "get_index_chart":
            from .tools.index_tools import get_index_chart
            result = await get_index_chart(
                market=arguments["market"],
                period=arguments.get("period", "1D"),
                interval=arguments.get("interval", "5m"),
                cache=cache,
                api_client=api_client
            )
            
        elif name == "get_market_summary":
            from .tools.market_tools import get_market_summary
            result = await get_market_summary(
                cache=cache,
                api_client=api_client
            )
            
        elif name == "get_sector_indices":
            from .tools.market_tools import get_sector_indices
            result = await get_sector_indices(
                market=arguments.get("market", "KOSPI"),
                cache=cache,
                api_client=api_client
            )
            
        elif name == "get_market_compare":
            from .tools.market_tools import get_market_compare
            result = await get_market_compare(
                date_from=arguments.get("date_from"),
                date_to=arguments.get("date_to"),
                cache=cache,
                api_client=api_client
            )
            
        else:
            raise ValueError(f"Unknown tool: {name}")
            
        return [TextContent(type="text", text=str(result))]
        
    except Exception as e:
        logger.error(f"Error in tool {name}: {str(e)}")
        return [TextContent(type="text", text=f"Error: {str(e)}")]


async def main():
    """Main server entry point"""
    logger.info(f"Starting {settings.server_name} v{settings.server_version}")
    
    try:
        # Test API client connection
        await api_client.test_connection()
        logger.info("API client connection successful")
        
        # Start stdio server
        async with stdio_server() as streams:
            await server.run(
                streams[0], streams[1], 
                server.create_initialization_options()
            )
            
    except Exception as e:
        logger.error(f"Server startup failed: {str(e)}")
        raise


if __name__ == "__main__":
    asyncio.run(main())