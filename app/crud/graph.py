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
from .tools import data_agent_tool, processar_documento_ocr
from ..core.config import GENAI_API_KEY

from typing import TypedDict, Annotated, List, Dict, Any, Optional
from langchain_core.messages import BaseMessage, HumanMessage
from langgraph.graph import StateGraph, START, END
from langgraph.prebuilt import create_react_agent
from langgraph.graph.message import add_messages
from .supervisor import PROMPT, RouteResponse

import logging

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AgentState(TypedDict):
    messages: Annotated[List[BaseMessage], add_messages]
    next: str
    # current_document_type: Optional[str]  # 'CAF' or 'DAP'
    # extracted_data: Optional[Dict[str, Any]]  # Store extracted data
    # user_tax_id: Optional[str]  # Store user CPF/CNPJ
    # requires_data_saving: bool  # Flag to indicate if data needs to be saved

class Graph:
    def __init__(self):
        self.llm = ChatOpenAI(model='gpt-4o')
        self.llm_genai = ChatGoogleGenerativeAI(
            api_key=GENAI_API_KEY,
            model="gemini-2.5-flash",
            temperature=0,
            max_tokens=None,
            timeout=None,
            max_retries=2,
        )

    def graph(self):
        """Create improved graph with better logic"""

        workflow = StateGraph(AgentState)

        # Add nodes
        workflow.add_node("Messenger_agent", self.messenger_node)
        workflow.add_node("supervisor", self.supervisor_node)

        # Define edges - SIMPLIFIED VERSION
        workflow.add_edge("Messenger_agent", "supervisor")
        workflow.add_edge(START, "supervisor")

        # Use supervisor's decision directly - NO OVERRIDE
        conditional_map = {
            "Messenger_agent": "Messenger_agent",
            "FINISH": END
        }
        
        workflow.add_conditional_edges(
            "supervisor",
            # Just use the supervisor's decision directly
            lambda state: state["next"],
            conditional_map
        )

        return workflow

    def messenger_node(self, state: AgentState) -> Dict[str, Any]:
        """Handle messenger agent with document processing"""
        print("\n" + "🔍 MESSENGER AGENT - Processing...")
        
        messenger_agent = create_react_agent(
            self.llm_genai, 
            tools=[processar_documento_ocr], # ,data_agent_tool
            state_modifier=MESSENGER_AGENT_PROMPT
        )
        
        # Check if there's a file to process
        last_message = state["messages"][-1].content if state["messages"] else ""
        if "[ARQUIVO:" in last_message:
            print("   📁 File detected in message, will use processar_documento_ocr tool")

        result = messenger_agent.invoke(state)
        
        # Check if document was processed and extract data
        # _____________________________------------------COLOCAR SOMENTE O RESULT E TIRAR EXTRACT_DATA
        # extracted_data = self.extract_data_from_response(result)

        # if extracted_data:
        #     # state["extracted_data"] = extracted_data
        #     # state["requires_data_saving"] = True
        #     print("   ✅ Document processed successfully, data extracted")
        #     print(f"   📊 Data type: {extracted_data.get('document_type', 'Unknown')}")
        # else:
        #     print("   💬 Regular conversation (no document processing)")
        
        response_content = result["messages"][-1].content
        print(f"   📨 Response: {response_content[:100]}..." if len(response_content) > 100 else f"   📨 Response: {response_content}")
        
        return {"messages": [HumanMessage(content=response_content, name="Messenger_agent")]}

    def supervisor_node(self, state: AgentState) -> Dict[str, Any]:
        """Improved supervisor with better decision logic"""
        print("\n" + "="*50)
        print("🔄 SUPERVISOR - Analyzing conversation...")
        
        # Show last few messages for context
        recent_messages = state["messages"][-3:] if len(state["messages"]) >= 3 else state["messages"]
        for i, msg in enumerate(recent_messages):
            sender = getattr(msg, 'name', 'user')
            content = msg.content[:200] + "..." if (len(str(msg.content)) > 200) and (isinstance(msg.content, str)) else msg.content
            print(f"   📝 {sender}: {content}")
        
        # Check for conversation completion conditions FIRST
        last_message_content = state["messages"][-1].content if state["messages"] else ""

        # If user is sending documents or needs document processing
        if any(keyword in last_message_content.lower() for keyword in ['.pdf', '.png', '.jpg', '.jpeg', '.gif', '.bmp', '.tiff']):
            return {"next": "Messenger_agent"}
        
        # If we've processed documents and the messenger is saying goodbye, FINISH
        if any(phrase in last_message_content.lower() for phrase in 
            ['obrigado', 'agradeço', 'finalizado', 'concluído', 'ajuda em algo mais']):
            print("🎯 SUPERVISOR: Conversation complete, sending to FINISH")
            return {"next": "FINISH"}
        
        # Otherwise, let the LLM decide
        supervisor_chain = (
            PROMPT
            | self.llm.with_structured_output(RouteResponse)
        )
        result = supervisor_chain.invoke(state)
        
        print(f"🎯 SUPERVISOR DECISION: {result.next}")
        
        return {"next": result.next}

    def get_processed_documents(self, state: AgentState) -> list:
        """Get list of processed document types from conversation history"""
        processed = []
        for message in state["messages"]:
            content = message.content if hasattr(message, 'content') else str(message)
            if "CAF" in content and "processado" in content.lower():
                processed.append("CAF")
            if "DAP" in content and "processado" in content.lower():
                processed.append("DAP")
        return list(set(processed))

    def extract_data_from_response(self, result: Dict) -> Optional[Dict]:
        """Extract structured data from agent response"""
        content = result["messages"][-1].content if result["messages"] else ""
        
        # Look for JSON-like structures or specific patterns in the response
        # This is a simplified version - you might want to use more sophisticated parsing
        try:
            import json
            import re
            
            # Try to find JSON in the response
            json_match = re.search(r'\{.*\}', content, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
            
            # Check for specific document indicators
            if any(indicator in content for indicator in ["Nº UFPA", "Nº CAF/DAP", "Nº DAP"]):
                # You might want to add more sophisticated parsing here
                # or modify the messenger agent to always return structured JSON
                return {"raw_content": content, "needs_processing": True}
                
        except Exception as e:
            logger.warning(f"Could not extract data from response: {e}")
        
        return None



# class AgentState(TypedDict):
#     # The annotation tells the graph that new messages will always
#     # be added to the current states
#     # messages: Annotated[Sequence[BaseMessage], operator.add]
#     messages: Annotated[list[AnyMessage], add_messages]
#     # The 'next' field indicates where to route to next
#     next: str

# def agent_node(state, agent, name):
#     result = agent.invoke(state)
#     return {"messages": [HumanMessage(content=result["messages"][-1].content, name=name)]}

# class Graph:

#     def __init__(self):
#         self.llm = ChatOpenAI(model='gpt-4o') # 'gpt-4.1-nano'
#         self.llm_genai = ChatGoogleGenerativeAI(api_key=GENAI_API_KEY,
#             model="gemini-2.5-flash",
#             temperature=0,
#             max_tokens=None,
#             timeout=None,
#             max_retries=2,
#             # other params...
#         )

#     def graph(self):
#         """Create graph"""

#         # db = PgConnection.connect()
#         # toolkit = SQLDatabaseToolkit(db=db,llm=self.llm)

#         msg_agent = create_react_agent(self.llm_genai, tools=[processar_documento_ocr], state_modifier=MESSENGER_AGENT_PROMPT)
#         msg_node = functools.partial(agent_node, agent=msg_agent, name="Messenger_agent")

#         data_agent = create_react_agent(self.llm, tools=[save_caf], state_modifier=DATA_AGENT_PROMPT)
#         data_node = functools.partial(agent_node, agent=data_agent, name="Data_agent")

#         workflow = StateGraph(AgentState)

#         workflow.add_node("Messenger_agent", msg_node)
#         workflow.add_node("Data_agent", data_node)
#         workflow.add_node("supervisor", supervisor_agent)

#         for member in members:
#             workflow.add_edge(member, "supervisor")

#         conditional_map = {k: k for k in members}
#         conditional_map["FINISH"] = END
#         workflow.add_conditional_edges("supervisor", lambda x: x["next"], conditional_map)
#         # Finally, add entrypoint
#         workflow.add_edge(START, "supervisor")

#         return workflow