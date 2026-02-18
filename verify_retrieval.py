
import asyncio
import logging
from search import QuerySearchEngine

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def verify():
    engine = QuerySearchEngine()
    
    # Test query that should retrieve the "top 5 customers" example
    test_query = "Who are the top customers by total sales amount?"
    
    logger.info(f"Testing Query: {test_query}")
    
    result = await engine.generate_sql_from_natural_language(test_query)
    
    logger.info("Generated SQL Result:")
    logger.info(result)
    
    await engine.close()

if __name__ == "__main__":
    asyncio.run(verify())
