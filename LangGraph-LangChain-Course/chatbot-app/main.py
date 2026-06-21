from langchain_community.adapters.openai import convert_openai_messages
from langchain_community.tools import TavilySearchResults
from langgraph.graph import StateGraph
from typing import Annotated

from langgraph.prebuilt import ToolNode, tools_condition
from typing_extensions import TypedDict
from langgraph.graph.message import add_messages
from langchain_openai import ChatOpenAI
from dotenv import load_dotenv, find_dotenv
from IPython.display import Image, display
from tavily import TavilyClient
import os

load_dotenv(find_dotenv(), override=True)
load_dotenv('.env.local', override=True)

tavily_tool = TavilySearchResults(max_results=3)
tools = [tavily_tool]
llm = ChatOpenAI(model='gpt-4o-mini', temperature=0.5)
llm_with_tools = llm.bind_tools(tools)

class State(TypedDict):
    messages: Annotated[list, add_messages]


def chatbot(state: State) -> TypedDict:
    return {'messages': [llm_with_tools.invoke(state['messages'])]}


def tavily_search(state: State, question: str) -> TypedDict:
    client = TavilyClient(api_key=os.getenv('TAIL_API_KEY'))

    response = client.search(
        query=question,
        search_depth='advanced',
        max_results=7,
        include_images=True,
        include_answer=True,
        include_raw_content=False,
    )

    results = response.get('results', [])

    prompt = [
        {
            'role': 'system',
            'content': f'''You are an AI critical research assistant.
            Your sole purpose is to write well written, obejective and structured reports on given text.
            '''
        },
        {
            'role': 'user',
            'content': f'''Information: """{results}"""
            Using the above information, answer the following query: """{question}""" in a detailed report
            '''
        }
    ]
    lc_messages = convert_openai_messages(prompt)
    tavily_response = ChatOpenAI(model='gpt-4o-mini', temperature=1).invoke(lc_messages)


def build_graph() -> StateGraph:
    tool_node = ToolNode(tools=tools)
    graph_builder = StateGraph(State)
    graph_builder.add_node('chatbot', chatbot)
    graph_builder.add_node('tools', tool_node)
    graph_builder.add_conditional_edges(
        'chatbot',
        tools_condition,
    )
    graph_builder.add_edge('tools', 'chatbot')
    graph_builder.set_entry_point('chatbot')
    # graph_builder.set_finish_point('chatbot')

    return graph_builder


def main():
    print("Hello from chatbot-app!")
    graph = build_graph()
    compiled = graph.compile()
    compiled.get_graph().draw_mermaid_png(output_file_path='graph.png')
    display(Image(compiled.get_graph().draw_mermaid_png()))


    while True:
        user_input = str(input("What do you want to do/ask?"))

        if user_input.lower() in ['quit', 'q', 'exit',' bye']:
            print("Goodbye!")
            break


        for event in compiled.stream({'messages': ('user', user_input)}):
            for value in event.values():
                print(f'Assistant: {value["messages"][-1].content}')
                print('-'*20)

if __name__ == "__main__":
    main()
