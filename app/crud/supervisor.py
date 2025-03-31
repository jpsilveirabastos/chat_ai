from langchain_core.messages import BaseMessage, HumanMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
import functools
import operator
from typing import Sequence, TypedDict, Annotated
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from typing import Union, Literal
from pydantic import BaseModel

from typing import Literal
from typing_extensions import TypedDict

from langchain_anthropic import ChatAnthropic
from langgraph.graph import MessagesState, END
from langgraph.types import Command
from langchain_openai import ChatOpenAI

from langgraph.graph.message import AnyMessage, add_messages

members = ["Messenger_agent","Whatsapp_agent","Sql_agent","Policy_agent"]

system_prompt = """Você é um supervisor da empresa Nagro e sua tarefa é gerenciar uma conversa entre os seguintes trabalhadores: {members}. Dada a seguinte solicitação do usuário, responda com o trabalhador para agir em seguida. 
Cada trabalhador executará uma tarefa e responderá com seus resultados e status. Se a conversa terminar, responda com 'FINISH'.

- **Messenger_agent**: Use este trabalhador para tarefas que envolvam:
    - Responder a perguntas simples, como: saudações e informações básicas.
- **Whatsapp_agent**: Use este trabalhador para tarefas que envolvam:
    - Mandar mensagem para os clientes no Whatsapp de forma natural.
    - SEMPRE usar o nome do cliente na mensagem.
- **Sql_agent**: Use este trabalhador para tarefas que envolvam:
    - Coletar pagamentos atrasados ​​no banco de dados.
    - Lidar com consultas que exigem análise de dados específicos, cálculos ou recuperação de bancos de dados SQL estruturados.
- **Policy_agent**: Use este trabalhador para tarefas que envolvam:
    - Consultar as políticas da empresa, como: do que se trata a empresa, como solicitar crédito, quais são os métodos de pagamento etc.

Critérios de decisão:
- **Messenger_agent** responder a perguntas simples que não envolvam as políticas da empresa ou contratos.
- **Whatsapp_agent** apenas envia mensagens de texto no Whatsapp para cobrar o cliente das suas dívidas.
- **Sql_agent** pega dados do banco de dados sobre os contratos.
- **Policy_agent** responde apenas sobre as políticas da empresa.

Se o **Policy_agent** precisar de alguma informação sobre contratos, roteie para **Sql_agent** para obter essas informações.
Use o **Sql_agent** para buscar número de telefone e o nome do cliente quando o **Whatsapp_agent** tiver que mandar mensagem no Whatsapp.
O **Whatsapp_agent** apenas vai ser chamado quando for necessário mandar mensagem para clientes no whatsapp a fim de cobrar as dívidas, o número de telefone deve ser buscado no banco de dados SQL e a mensagem deve conter o nome do cliente que também está no banco de dados SQL.
"""

options = ["FINISH"] + members

RouteResponseNextType = Union[Literal["FINISH"], Literal["Messenger_agent"],
                              Literal["Policy_agent"], Literal["Sql_agent"], Literal["Whatsapp_agent"]]
class RouteResponse(BaseModel):
    next: RouteResponseNextType

prompt = ChatPromptTemplate.from_messages(
    [
        ("system", system_prompt),
        MessagesPlaceholder(variable_name="messages"),
        (
            "system",
            "Dado a conversa acima, quem deve agir em seguida?" # "Given the conversation above, who should act next?"
            " Ou deveríamos finalizar com FINISH? Selecione um desses: {options}", # Or should we FINISH? Select one of
        ),
    ]
).partial(options=str(options), members=", ".join(members))

llm = ChatOpenAI(model='gpt-4o')

def supervisor_agent(state):
    supervisor_chain = (
        prompt
        | llm.with_structured_output(RouteResponse)
    )
    return supervisor_chain.invoke(state)