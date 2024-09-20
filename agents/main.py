import asyncio
import logging
from agent import Reddtriever
from search import SearchTool

async def main():
    reddtriever = Reddtriever()
    search_tool = SearchTool()

    await reddtriever.initialize()
    await search_tool.initialize()

    while True:
        query = input("Enter your query (or 'quit' to exit): ")
        if query.lower() == 'quit':
            break

        response = await reddtriever.generate(query)
        print(response)


if __name__ == "__main__":
    asyncio.run(main())
    asyncio.run(main())
