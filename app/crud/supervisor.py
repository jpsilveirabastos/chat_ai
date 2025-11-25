# from langchain_core.messages import BaseMessage, HumanMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from typing import Union, Literal
from pydantic import BaseModel
from typing import Literal, Dict, Any

from langchain_openai import ChatOpenAI

members = ["Messenger_agent"]

system_prompt = """Você é um supervisor da empresa Nagro e sua tarefa é decidir quem vai ser o próximo agente a agir.
Existem os agentes: 'Messenger_agent'.
O 'Messenger_agent' tem a função de comunicar com o usuário e ler os documentos que este enviar, interpretar os dados e salvá-los no banco de dados.
Analise as mensagens anteriores, se o usuário enviou uma mensagem e o Messenger_agent respondeu, finalize com 'FINISH', NÃO RETORNE 'Messenger_agent' MAIS DO QUE UMA VEZ CONSECUTIVA.
Assim que gerar alguma resposta, finalize com 'FINISH' para enviá-la ao usuário e assim começar a próxima iteração.

- **Messenger_agent**: Use este trabalhador para tarefas que envolvam:
    - Interagir com o usuário, passando pelas perguntas necessárias conforme o histórico da conversa.
    - Responder a perguntas simples, como: saudações e informações básicas.
    - Ler documentos.

P.S.1: Se o Messenger_agent respondeu à pergunta, finalize com 'FINISH' para que a resposta seja enviada ao usuário. NÃO RETORNE 'Messenger_agent' MAIS DO QUE UMA VEZ CONSECUTIVA.
P.S.2: Analise a última mensagem, quando o "Usuário" for o último que enviou a mensagem, SEMPRE repasse para algum agente.
"""

options = ["FINISH"] + members

RouteResponseNextType = Union[Literal["FINISH"], Literal["Messenger_agent"]]
class RouteResponse(BaseModel):
    next: RouteResponseNextType

PROMPT = ChatPromptTemplate.from_messages(
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

llm = ChatOpenAI(model='gpt-4o') # 'gpt-4.1-nano'

def supervisor_agent(state):
    supervisor_chain = (
        PROMPT
        | llm.with_structured_output(RouteResponse)
    )
    return supervisor_chain.invoke(state)