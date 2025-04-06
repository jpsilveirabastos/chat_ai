import functools
import operator
from typing import Sequence, TypedDict, Annotated
import uuid
from typing import Union, Literal
from pydantic import BaseModel
from typing import Literal
from typing_extensions import TypedDict

from langchain_core.messages import BaseMessage, HumanMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

from langchain_anthropic import ChatAnthropic
from langgraph.graph import MessagesState, END
from langgraph.types import Command
from langchain_openai import ChatOpenAI

from langchain.llms.openai import OpenAI

from langchain.agents import create_sql_agent
from langchain.agents.agent_toolkits import SQLDatabaseToolkit
from langchain.agents import AgentExecutor

from langchain.sql_database import SQLDatabase
from langgraph.checkpoint.memory import MemorySaver

import psycopg2

from langchain_core.tools import tool
from langchain_core.messages import HumanMessage
from langgraph.graph import StateGraph, START, END
from langgraph.prebuilt import create_react_agent

from langgraph.graph.message import AnyMessage, add_messages

from ..core.db import PgConnection
from .supervisor import supervisor_agent, members
from .agents import MSSQL_AGENT_SUFFIX_WITH_MEMORY, POLICY_AGENT_SUFFIX_WITH_MEMORY, MESSENGER_AGENT_SUFFIX_WITH_MEMORY, WHATSAPP_AGENT_SUFFIX_WITH_MEMORY
from .tools import twilio_wpp_messages

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
        self.llm = ChatOpenAI(model='gpt-4o')

    def graph(self):
        """Create graph"""

        db = PgConnection.connect()
        toolkit = SQLDatabaseToolkit(db=db,llm=self.llm)

        msg_agent = create_react_agent(self.llm, tools=[], state_modifier=MESSENGER_AGENT_SUFFIX_WITH_MEMORY)
        msg_node = functools.partial(agent_node, agent=msg_agent, name="Messenger_agent")

        wpp_agent = create_react_agent(self.llm, tools=[twilio_wpp_messages], state_modifier=WHATSAPP_AGENT_SUFFIX_WITH_MEMORY)
        wpp_node = functools.partial(agent_node, agent=wpp_agent, name="Whatsapp_agent")

        sql_agent = create_react_agent(self.llm, tools=toolkit.get_tools(), state_modifier=MSSQL_AGENT_SUFFIX_WITH_MEMORY)
        sql_node = functools.partial(agent_node, agent=sql_agent, name="Sql_agent")

        pol_agent = create_react_agent(self.llm, tools=[], state_modifier=POLICY_AGENT_SUFFIX_WITH_MEMORY)
        pol_node = functools.partial(agent_node, agent=pol_agent, name="Policy_agent")

        workflow = StateGraph(AgentState)

        workflow.add_node("Messenger_agent", msg_node)
        workflow.add_node("Whatsapp_agent", wpp_node)
        workflow.add_node("Policy_agent", pol_node)
        workflow.add_node("Sql_agent", sql_node)
        workflow.add_node("supervisor", supervisor_agent)

        for member in members:
            # We want our workers to ALWAYS "report back" to the supervisor when done
            workflow.add_edge(member, "supervisor")
        # The supervisor populates the "next" field in the graph state
        # which routes to a node or finishes
        conditional_map = {k: k for k in members}
        conditional_map["FINISH"] = END
        workflow.add_conditional_edges("supervisor", lambda x: x["next"], conditional_map)
        # Finally, add entrypoint
        workflow.add_edge(START, "supervisor")

        memory = MemorySaver()
        graph = workflow.compile(checkpointer=memory)

        return graph