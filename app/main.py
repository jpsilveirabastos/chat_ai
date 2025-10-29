from fastapi import Depends, Header, FastAPI, status, HTTPException, Form, Response
from fastapi.responses import JSONResponse
from fastapi import status, HTTPException, Header
# from twilio.twiml.messaging_response import MessagingResponse
from typing import Optional, Any, Dict
import uuid
import json
import requests
# from langchain_core.messages import HumanMessage
from langgraph.checkpoint.postgres import PostgresSaver

from .core.config import AUTH_KEY, DB_URI, TWILIO_SID, TWILIO_AUTH_TOKEN
from .crud.langgraph import Graph

app = FastAPI()

class AuthToken:

    def __call__(self, x_api_key: Optional[str] = Header(...)):
 
        if x_api_key != AUTH_KEY:
            raise HTTPException(status_code=401, detail="unauthorized")
 
        return x_api_key
    
@app.post('/id_produtor/')
def call_agents(input: str):

    input_text = input

    workflow = Graph().graph()
    config = {"configurable": {'thread_id': '29-10-25-1'}, "recursion_limit": 3000}

    with PostgresSaver.from_conn_string(DB_URI) as checkpointer:
        graph = workflow.compile(checkpointer=checkpointer)
        input_data = {"messages": input_text}
        # print(f"input: {input_data}")
        resp = graph.invoke(input_data, config=config, stream_mode='values')
        # print(resp)
        resp_filt = resp['messages'][-1].content
        # print(resp_filt)

    return resp_filt

# @app.post('/query/')
# def call_graph(
#     From: str = Form(...),
#     Body: str = Form(""),  # Pode vir vazio se for só mídia
#     NumMedia: int = Form(0),
#     MediaUrl0: str = Form(None),
#     MediaContentType0: str = Form(None),
# ):
#     """Receives a WhatsApp message with optional media (e.g., PDF)"""

#     response = MessagingResponse()
#     input_text = Body

#     # Se houver mídia e for um PDF
#     if NumMedia > 0 and MediaContentType0 == "application/pdf":
#         # Baixa o conteúdo do PDF
#         pdf_response = requests.get(MediaUrl0, auth=(TWILIO_SID, TWILIO_AUTH_TOKEN))
#         if pdf_response.status_code == 200:
#             # Aqui você pode processar o PDF e extrair texto
#             from io import BytesIO
#             import fitz  # PyMuPDF

#             pdf_text = ""
#             with fitz.open(stream=BytesIO(pdf_response.content), filetype="pdf") as doc:
#                 # print(doc)
#                 for page in doc:
#                     pdf_text += page.get_text()

#             input_text += "\n[Conteúdo do PDF]:\n" + pdf_text.strip()
#         else:
#             input_text += "\n[Erro ao baixar o PDF]"

#     workflow = Graph().graph()
#     config = {"configurable": {'thread_id': From}, "recursion_limit": 3000}

#     with PostgresSaver.from_conn_string(DB_URI) as checkpointer:
#         graph = workflow.compile(checkpointer=checkpointer)
#         input_data = {"messages": input_text}
#         print(input_data)
#         resp = graph.invoke(input_data, config=config, stream_mode='values')
#         # print(resp)
#         resp_filt = resp['messages'][-1].content
#         print(resp_filt)

#     msg = response.message(resp_filt)
#     return Response(content=str(response), media_type="application/xml")

# @app.post('/query/') # , dependencies=[Depends(AuthToken())]
# def call_graph(From: str = Form(...), Body: str = Form(...)): # : Dict[Any,Any]
#     """Receives a query as string and return the response"""

#     response = MessagingResponse()

#     workflow = Graph().graph()
#     # session_id = 'abcda' #uuid.uuid4()
#     config = {"configurable": {'thread_id': From}, "recursion_limit": 10}

#     with PostgresSaver.from_conn_string(DB_URI) as checkpointer:
#         graph = workflow.compile(checkpointer=checkpointer)
#         input_data = {"messages": Body} # request['query']}
#         print(input_data)
#         # input_data = {"messages":[HumanMessage(content=request['query'])]}
#         resp = graph.invoke(input_data, config=config, stream_mode='values')
#         resp_filt = resp['messages'][-1].content
#         print(resp_filt)
        
#     msg = response.message(resp_filt)

#     return Response(content=str(response), media_type="application/xml")

@app.get("/health-check",
            tags=['Health Check'],
            description='Rota para verificação de status de disponibilidade da API',
            summary='Check de disponibilidade',
            status_code=status.HTTP_200_OK,
            name="Health check"
            )
def health():
    return JSONResponse(content='Ok', status_code=status.HTTP_200_OK)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="127.0.0.1", port=8080, reload=True)