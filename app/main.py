from fastapi import Depends, Header, FastAPI, status, HTTPException, Form, Response
from fastapi.responses import JSONResponse
from fastapi import status, HTTPException, Header
from typing import Optional, Any, Dict
import uuid
import json
import requests
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
