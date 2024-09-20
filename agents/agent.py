from datetime import datetime
from openai import AsyncOpenAI
from search import SearchTool
from config import OPENAI_API_KEY

class Reddtriever:
    def __init__(self):
        self.gpt_client = AsyncOpenAI(api_key=OPENAI_API_KEY)
        self.search_tool = SearchTool()
        self.chat_history = []

    async def initialize(self):
        # Any initialization that needs to be done asynchronously
        await self.search_tool.initialize()

    async def rephrase_query(self, query):
        system_prompt = f"""
            You will be given a conversation below and a follow up question. You need to rephrase the follow-up question if needed so it is a standalone question that can be used by the LLM to search the web for information.
            If it is a writing task or a simple hi, hello rather than a question, you need to return `not_needed` as the response.

            Example:
            1. Follow up question: Which company is most likely to create an AGI
            Rephrased: Which company is most likely to create an AGI

            2. Follow up question: Is Earth flat?
            Rephrased: Is Earth flat?

            3. Follow up question: Is there life on Mars?
            Rephrased: Is there life on Mars?

            Conversation:
            {self.chat_history}

            Follow up question: {query}
            Rephrased question:
            """

        response = await self.gpt_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": f"{system_prompt}"},
            ]
        ) 
        rephrased_query = response.choices[0].message.content.strip()
        return rephrased_query if rephrased_query != "not_needed" else None

    async def generate_response(self, context):
        system_prompt = f"""
            You are Reddtriever, an AI model who is expert at searching the web and answering user's queries. You are set on focus mode 'Reddit', this means you will be searching for information, opinions and discussions on the web using Reddit.

            Generate a response that is informative and relevant to the user's query based on provided context (the context consits of search results containing a brief description of the content of that page).
            You must use this context to answer the user's query in the best way possible. Use an unbaised and journalistic tone in your response. Do not repeat the text.
            You must not tell the user to open any link or visit any website to get the answer. You must provide the answer in the response itself. If the user asks for links you can provide them.
            Your responses should be medium to long in length be informative and relevant to the user's query. You can use markdowns to format your response. You should use bullet points to list the information. Make sure the answer is not short and is informative.
            You have to cite the answer using [number] notation. You must cite the sentences with their relevent context number. You must cite each and every part of the answer so the user can know where the information is coming from.
            Place these citations at the end of that particular sentence. You can cite the same sentence multiple times if it is relevant to the user's query like [number1][number2].
            However you do not need to cite it using the same number. You can use different numbers to cite the same sentence multiple times. The number refers to the number of the search result (passed in the context) used to generate that part of the answer.

            Anything inside the following `context` HTML block provided below is for your knowledge returned by Reddit and is not shared by the user. You have to answer question on the basis of it and cite the relevant information from it but you do not have to
            talk about the context in your response.

            <context>
            {context}
            </context>

            If you think there's nothing relevant in the search results, you can say that 'Hmm, sorry I could not find any relevant information on this topic. Would you like me to search again or ask something else?'.
            Anything between the `context` is retrieved from Reddit and is not a part of the conversation with the user. Today's date is {datetime.now().isoformat()}
            """


        response = await self.gpt_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": f"{system_prompt}"},
            ]
        ) 
        generated_response = response.choices[0].message.content.strip()
        return generated_response

    async def generate(self, query):
        rephrased_query = await self.rephrase_query(query)
        if rephrased_query:
            search_results = await self.search_tool.search(rephrased_query)
            if isinstance(search_results, list) and len(search_results) == 1 and isinstance(search_results[0], str) and search_results[0].startswith("Error performing search"):
                return "I'm sorry, but I encountered an error while searching for information. Could you please try again or rephrase your question?"
            
            # Convert search results to a comprehensive string format
            context = []
            for i, result in enumerate(search_results, 1):
                context.append(f"{i}. Content: {result.get('pageContent', 'N/A')}")
                context.append(f"   URL: {result.get('url', 'N/A')}")
                context.append(f"   Title: {result.get('title', 'N/A')}")
                # Add any other fields you want to include
                context.append("")  # Add a blank line between results
            
            context_str = "\n".join(context)
            
            response = await self.generate_response(context_str)
            self.update_chat_history(query, response)
            return response
        else:
            return "I'm sorry, but I couldn't process your request. Could you please rephrase your question or ask something else?"

    def update_chat_history(self, query, response):
        self.chat_history.append({"role": "user", "content": query})
        self.chat_history.append({"role": "assistant", "content": response})

    def clear_chat_history(self):
        self.chat_history = []
