# from langchain_core.messages import BaseMessage, HumanMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from typing import Union, Literal
from pydantic import BaseModel

from typing import Literal

from langchain_openai import ChatOpenAI

members = ["Messenger_agent", "Data_agent"]

system_prompt = """Você é um supervisor da empresa Nagro e sua tarefa é decidir quem vai ser o próximo agente a agir.
Existem os agentes: 'Messenger_agent' e 'Data_agent'.
O 'Messenger_agent' tem a função de comunicar com o usuário e ler os documentos que este enviar, enquanto o 'Data_agent' tem a função de interpretar os dados e salvá-los no banco de dados.
O 'Data_agent' vai ser chamado APENAS quando há documentos enviados pelo usuário, caso contrário não é necessário chamar ele.
Se o 'Data_agent' não tiver a necessidade de ser chamado, use somente o 'Messenger_agent' para responder o usuário.
Sempre que o usuário enviar arquivos de documentos, o 'Messenger_agent' lê o documento e repassa as informações para VOCê, e depois você repassa para o 'Data_agent'. Depois o 'Messenger_agent' responde o usuário.
Assim que gerar alguma resposta para o usuário, finalize com 'FINISH' para enviar a resposta ao usuário e assim começar a próxima interação.

- **Messenger_agent**: Use este trabalhador para tarefas que envolvam:
    - Interagir com o usuário, passando pelas perguntas necessárias conforme o histórico da conversa.
    - Responder a perguntas simples, como: saudações e informações básicas.
    - Ler documentos.
- **Data_agent**: Use este trabalhador para tarefas que envolvam:
    - Interpretar documentos e salvá-los no banco de dados.
"""

options = ["FINISH"] + members

RouteResponseNextType = Union[Literal["FINISH"], Literal["Messenger_agent"], Literal["Data_agent"]]
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

llm = ChatOpenAI(model='gpt-4o') # 'gpt-4.1-nano'

def supervisor_agent(state):
    supervisor_chain = (
        prompt
        | llm.with_structured_output(RouteResponse)
    )
    return supervisor_chain.invoke(state)