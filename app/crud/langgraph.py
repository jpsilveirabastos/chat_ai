import functools
from typing import Sequence, TypedDict, Annotated
from typing_extensions import TypedDict

from langchain_core.messages import BaseMessage, HumanMessage

from langchain_openai import ChatOpenAI
from langchain_google_genai import ChatGoogleGenerativeAI

from langchain_core.tools import tool
from langchain_core.messages import HumanMessage
from langgraph.graph import StateGraph, START, END
from langgraph.prebuilt import create_react_agent

from langgraph.graph.message import AnyMessage, add_messages

from ..core.db import PgConnection
from .supervisor import supervisor_agent, members
from .agents import MESSENGER_AGENT_PROMPT, DATA_AGENT_PROMPT
from .tools import save_caf, processar_documento_ocr
from ..core.config import GENAI_API_KEY

class AgentState(TypedDict):
    # The annotation tells the graph that new messages will always
    # be added to the current states
    # messages: Annotated[Sequence[BaseMessage], operator.add]
    messages: Annotated[list[AnyMessage], add_messages]
    # The 'next' field indicates where to route to next
    next: str

def agent_node(state, agent, name):
    result = agent.invoke(state)
    return {"messages": [HumanMessage(content=result["messages"][-1].content, name=name)]}

class Graph:

    def __init__(self):
        self.llm = ChatOpenAI(model='gpt-4o') # 'gpt-4.1-nano'
        self.llm_genai = ChatGoogleGenerativeAI(api_key=GENAI_API_KEY,
            model="gemini-2.5-flash",
            temperature=0,
            max_tokens=None,
            timeout=None,
            max_retries=2,
            # other params...
        )

    def graph(self):
        """Create graph"""

        # db = PgConnection.connect()
        # toolkit = SQLDatabaseToolkit(db=db,llm=self.llm)

        msg_agent = create_react_agent(self.llm_genai, tools=[processar_documento_ocr], state_modifier=MESSENGER_AGENT_PROMPT)
        msg_node = functools.partial(agent_node, agent=msg_agent, name="Messenger_agent")

        data_agent = create_react_agent(self.llm, tools=[save_caf], state_modifier=DATA_AGENT_PROMPT)
        data_node = functools.partial(agent_node, agent=data_agent, name="Data_agent")

        workflow = StateGraph(AgentState)

        workflow.add_node("Messenger_agent", msg_node)
        workflow.add_node("Data_agent", data_node)
        workflow.add_node("supervisor", supervisor_agent)

        for member in members:
            workflow.add_edge(member, "supervisor")

        conditional_map = {k: k for k in members}
        conditional_map["FINISH"] = END
        workflow.add_conditional_edges("supervisor", lambda x: x["next"], conditional_map)
        # Finally, add entrypoint
        workflow.add_edge(START, "supervisor")

        return workflow