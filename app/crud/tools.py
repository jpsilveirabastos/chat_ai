from langchain_community.utilities.twilio import TwilioAPIWrapper
from langchain_core.tools import tool

@tool
def twilio_wpp_messages(mensagem: str, telefone: str):
    """Use esta ferramenta para mandar mensagens de texto pelo whatsapp.
    Coloque como input a mensagem de texto e o telefone para o qual a mensagem vai ser enviada"""
    
    twilio = TwilioAPIWrapper(
        account_sid="ACf3a0a93b609a0bfa25bd892dec9b87fb",
        auth_token="2024a69123dc0bb03b81ea9a489256ec",
        from_number="whatsapp:+14155238886"
    )
    resp = twilio.run(body=mensagem, to=f"whatsapp:+55{telefone}")
    return resp