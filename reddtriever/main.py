import asyncio
from agent import Reddtriever
from search import SearchTool
from utils import log_interaction 

async def main():
    reddtriever = Reddtriever()
    search_tool = SearchTool()

    await reddtriever.initialize()
    await search_tool.initialize()

    while True:
        query = input("Enter your query (or 'quit' to exit): ")
        if query.lower() == 'quit':
            break

        response, docs_retrieved, rephrased_query = await reddtriever.generate(query)
        print("="*100)
        print(response)

        await log_interaction(query, docs_retrieved, response, rephrased_query)

if __name__ == "__main__":
    asyncio.run(main())
