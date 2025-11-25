from fastapi import Depends, Header, Form, Body, File, FastAPI, status, HTTPException, UploadFile
from fastapi.responses import JSONResponse
from typing import Optional, Any, Dict
import tempfile
import shutil
import os
from langchain_core.messages import HumanMessage
from langgraph.checkpoint.postgres import PostgresSaver

from .core.config import AUTH_KEY, DB_URI
from .crud.graph import Graph
from .crud.tools import comprovante_renda_ocr, data_agent_tool
from .crud.crm_data import get_file_data, save_ocr_data

import logging

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()

class AuthToken:

    def __call__(self, x_api_key: Optional[str] = Header(...)):
 
        if x_api_key != AUTH_KEY:
            raise HTTPException(status_code=401, detail="unauthorized")
 
        return x_api_key

@app.post('/ocr_renda/', dependencies=[Depends(AuthToken())])
async def ocr_renda(request: Dict[str, Any] = Body(...)):

    content = get_file_data(request.get("file_id"))
    
    extracted_content = comprovante_renda_ocr.invoke({
        "resp_file": content
    })

    result = save_ocr_data(extracted_content, request.get('deal_id'))

    return JSONResponse(content=extracted_content, status_code=status.HTTP_200_OK)

@app.post('/save_data/', dependencies=[Depends(AuthToken())])
async def save_data(request: Dict[str, Any] = Body(...)):

    extracted_content = request.get('extracted_content')
    
    result = data_agent_tool.invoke({
        "extracted_data": extracted_content
    })

    return JSONResponse(content=extracted_content, status_code=status.HTTP_200_OK)

@app.post('/id_produtor/', dependencies=[Depends(AuthToken())])
async def call_agents(
    input: Optional[str] = Form(None),
    file: Optional[UploadFile] = File(None),
):
    try:
        session_id = 'aaunguinf nga aaaaaaaaaaaa'

        print("\n" + "🚀" * 20)
        print("🚀 NEW API REQUEST RECEIVED")
        print(f"🚀 Input: {input}")
        print(f"🚀 File: {file.filename if file else 'None'}")
        print(f"🚀 Session ID: {session_id}")
        print("🚀" * 20 + "\n")
        
        workflow = Graph().graph()
        
        config = {
            "configurable": {
                'thread_id': session_id
            }, 
            "recursion_limit": 50
        }

        # Handle file upload
        temp_file_path = None
        user_input = input or ""
        
        if file and file.filename:
            # Save uploaded file to temporary location
            temp_dir = tempfile.gettempdir()
            temp_file_path = os.path.join(temp_dir, file.filename)
            
            with open(temp_file_path, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)
            
            # Add file path to user input
            user_input = f"{user_input} [ARQUIVO: {temp_file_path}]" if user_input else f"[ARQUIVO: {temp_file_path}]"
            print(f"📁 File saved to: {temp_file_path}")

        with PostgresSaver.from_conn_string(DB_URI) as checkpointer:
            graph = workflow.compile(checkpointer=checkpointer)
            
            input_data = {
                "messages": [HumanMessage(content=user_input, name="Usuário")],
                "next": "supervisor"
            }
            
            print("🔄 Starting graph execution...")
            final_state = None
            for step in graph.stream(input_data, config=config, stream_mode='values'):
                final_state = step
                print("📦 Graph step completed")
            
            # Clean up temporary file
            if temp_file_path and os.path.exists(temp_file_path):
                os.remove(temp_file_path)
                print(f"🧹 Temporary file cleaned: {temp_file_path}")
            
            if final_state and 'messages' in final_state and final_state['messages']:
                last_message = final_state['messages'][-1]
                resp_filt = last_message.content if hasattr(last_message, 'content') else str(last_message)
            else:
                resp_filt = "Processamento concluído."

            print(f"✅ FINAL RESPONSE: {resp_filt}")
            print("🏁 Request processing completed\n")

        return {"response": resp_filt, "session_id": session_id}

    except Exception as e:
        # Clean up on error
        if 'temp_file_path' in locals() and temp_file_path and os.path.exists(temp_file_path):
            os.remove(temp_file_path)
        print(f"❌ ERROR: {e}")
        logger.error(f"Error in agent processing: {e}")
        raise
        # raise HTTPException(status_code=500, detail=f"Erro no processamento: {str(e)}")
    
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