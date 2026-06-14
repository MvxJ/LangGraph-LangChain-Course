from pyexpat.errors import messages

from dotenv import load_dotenv, find_dotenv
from openai import OpenAI
import openai
import re
import httpx
import os

load_dotenv(find_dotenv())
load_dotenv('.env.local', override=True)

_MODEL = 'gpt-4o-mini'
_PROMPT = 'Write something short but funny, This should be a funny fact or some joke.'
_ACTION_RE = re.compile(r'^Action: (\w+): (.*)$')
_SYSTEM_PROMPT = """
You run in a loop of Thought, Action, PAUSE, Observation.
At the end of the loop you output an Answer
Use Thought to describe your thoughts about the question you have been asked.
Use Action to run one of the actions available to you - then return PAUSE.
Observation will be the result of running those actions.

Your available actions are:

calculate:
e.g calculate 4 * 7 / 3
Runs a calculation and returns the number - uses Python so be sure to use floating

get_cost:
e.g get_cost: book
returns the cost of book

wikipedia:
e.g wikipedia: LangChain
Returns a summary from searchin Wikipedia

Always look things up on Wikipedia if you have the opportunity to do so.

Example session #1:

Question: How much does a pen cost?
Thought: I should look the pen cost using get_cost
Action: get_cost: pen
PAUSE

You will be called again with this:

Observation: A pen costs $5

You then output:

Answer: A pen costs $5


Example session #2:

Question: What is the capital of France?
Thought: I should look the information about France on Wikipedia
Action: wikipedia: France
PAUSE

You will be called again with this:

Observation: A France capital is Paris

You then output:

Answer: A France capital is Paris
"""
client = OpenAI()

class ReActAgent:
    def __init__(self, system: str = ''):
        self.system = system
        self.messages = []

        if self.system:
            self.messages.append({'role': 'system', 'content': system})

    def __call__(self, prompt: str):
        self.messages.append({'role': 'user', 'content': prompt})
        result = self.execute()
        self.messages.append({'role': 'assistant', 'content': result})

        return result

    def execute(self, model: str = 'gpt-4', temperature: float = 0.0):
        completion = client.chat.completions.create(
            model=model,
            temperature=temperature,
            messages=self.messages,
        )

        return completion.choices[0].message.content


def query(question: str, max_turns: int = 5):
    counter = 0
    agent = ReActAgent(_SYSTEM_PROMPT)
    next_prompt = question
    while counter < max_turns:
        result = agent(next_prompt)
        counter += 1
        print(result)

        actions = [
            _ACTION_RE.match(a) for a in result.split('\n') if _ACTION_RE.match(a)
        ]

        if actions:
            action, action_input = actions[0].groups()

            if action not in known_actions:
                raise Exception('Unknown action')

            print(f'Action: {action} {action_input}')
            observation = known_actions[action](action_input)
            print(f'Observation:', {observation})
            next_prompt = f'Observation: {observation}'
        else:
            return

def calculate(what):
    eval(what)

def get_cost(thing):
    if thing in 'pen':
        return 'A pen costs $5'
    elif thing in 'book':
        return 'A book costs $15'
    elif thing in 'stapler':
        return 'A stapler costs $10'
    else:
        return 'A {thing} costs $8'.format(thing=thing)

def wikipedia(search):
    response = httpx.get(
        'https://en.wikipedia.org/w/api.php',
        params={
            'action': 'query',
            'list': 'search',
            'srsearch': search,
            'format': 'json',
        },
        headers={
            "User-Agent": "ReActAgentCourse/1.0 (maksymilianjachymczak@gmail.com)"
        }

    )
    print(response)
    result = response.json().get('query').get('search', [])

    if not result:
        return  None

    return result[0].get('snippet', '')

known_actions = {
    'wikipedia': wikipedia,
    'get_cost': get_cost,
    'calculate': calculate,
}

def main():
    # chat_completion = client.chat.completions.create(
    #     model=_MODEL,
    #     messages=[{'role': 'user', 'content': _PROMPT}]
    # )

    # print(chat_completion.choices[0].message.content)
    # agent = ReActAgent(_SYSTEM_PROMPT)
    # result = agent('How much pen costs?')
    # print(result)
    #
    # next_prompt = f"Observation: {get_cost('pen')}"
    # response = agent(next_prompt)
    # print(response)

    query(question='I need to buy 2 pens and a book how much will i Pay?')
if __name__ == "__main__":
    main()
