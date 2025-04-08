from fastapi import Depends, Header, FastAPI, status, HTTPException
from fastapi.responses import JSONResponse
from fastapi import status, HTTPException, Header
from typing import Optional, Any, Dict
import uuid
import json
from langchain_core.messages import HumanMessage
from langgraph.checkpoint.postgres import PostgresSaver

from .core.config import AUTH_KEY, DB_URI
from .crud.langgraph import Graph

app = FastAPI()

class AuthToken:

    def __call__(self, x_api_key: Optional[str] = Header(...)):
 
        if x_api_key != AUTH_KEY:
            raise HTTPException(status_code=401, detail="unauthorized")
 
        return x_api_key

@app.post('/query/', dependencies=[Depends(AuthToken())])
def call_graph(request: Dict[Any,Any]):
    """Receives a query as string and return the response"""

    query = request['query']
    workflow = Graph().graph()
    session_id = 'abcd' #uuid.uuid4()
    config = {"configurable": {'thread_id': session_id}, "recursion_limit": 10}

    with PostgresSaver.from_conn_string(DB_URI) as checkpointer:
        graph = workflow.compile(checkpointer=checkpointer)
        input_data = {"messages": query} # request['query']}
        # input_data = {"messages":[HumanMessage(content=request['query'])]}
        resp = graph.invoke(input_data, config=config, stream_mode='values')
        resp_filt = resp['messages'][-1].content

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