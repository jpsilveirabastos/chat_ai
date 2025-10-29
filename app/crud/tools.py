from langchain_community.utilities.twilio import TwilioAPIWrapper
from langchain_core.tools import tool
from ..core.config import TWILIO_SID, TWILIO_AUTH_TOKEN

import base64
from typing import Dict, Any, Union
# from langchain_google_vertexai import ChatVertexAI
from langchain_core.messages import HumanMessage
from langchain_core.tools import tool
from langchain_google_genai import ChatGoogleGenerativeAI
import os
from dotenv import load_dotenv
import fitz  # PyMuPDF
from PIL import Image, ImageEnhance, ImageFilter
import io
import cv2
import numpy as np

import re
import psycopg2
import logging

from ..core.config import GENAI_API_KEY

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

llm_genai = ChatGoogleGenerativeAI(api_key=GENAI_API_KEY,
            model="gemini-2.5-flash",
            temperature=0,
            max_tokens=None,
            timeout=None,
            max_retries=2,
            # other params...
        )

@tool
def twilio_wpp_messages(mensagem: str, telefone: str):
    """Use esta ferramenta para mandar mensagens de texto pelo whatsapp.
    Coloque como input a mensagem de texto e o telefone para o qual a mensagem vai ser enviada"""
    
    twilio = TwilioAPIWrapper(
        account_sid=TWILIO_SID,
        auth_token=TWILIO_AUTH_TOKEN,
        from_number="whatsapp:+14155238886"
    )
    resp = twilio.run(body=mensagem, to=f"whatsapp:+55{telefone}")
    return resp

@tool
def save_caf(caf_data: dict):
    """Use esta ferramenta para salvar as informações do Cadastro Nacional de Agricultura Familiar (CAF).
    O input 'caf_data' deve ser um dicionário com as seguintes variáveis e seus tipos:
    numero_caf varchar(100), situacao varchar(100), tax_id varchar(100), nome varchar(255), data_inscricao date, ultima_atualizacao date, data_validade date, cep varchar(50),  
    uf varchar(100), cidade varchar(255), endereco varchar(255), numero varchar(100), bairro varchar(255), complemento varchar(100), entidade varchar(100), cnpj varchar(100), cadastrador varchar(100),
    atividade_principal varchar(100), area_imovel numeric(16,2), renda numeric(16,2), produto varchar(255), renda_externa numeric(16,2), produto_externo varchar(255)
    """

    conn = psycopg2.connect(dbname="postgres", user="postgres", password="1673", host=r"localhost")
    cur = conn.cursor()

    query = """
        INSERT INTO caf (
            numero_caf, situacao, tax_id, nome, data_inscricao, ultima_atualizacao, 
            data_validade, cep, uf, cidade, endereco, numero, bairro, complemento, 
            entidade, cnpj, cadastrador, atividade_principal, area_imovel, renda, 
            produto, renda_externa, produto_externo
        ) VALUES (
            %(numero_caf)s, %(situacao)s, %(tax_id)s, %(nome)s, %(data_inscricao)s, 
            %(ultima_atualizacao)s, %(data_validade)s, %(cep)s, %(uf)s, %(cidade)s, 
            %(endereco)s, %(numero)s, %(bairro)s, %(complemento)s, %(entidade)s, 
            %(cnpj)s, %(cadastrador)s, %(atividade_principal)s, %(area_imovel)s, 
            %(renda)s, %(produto)s, %(renda_externa)s, %(produto_externo)s
        )"""
    
    cur.execute(query, caf_data)
    conn.commit()

    logger.info(f"CAF {caf_data.get('numero_caf')} salvo/atualizado com sucesso")

def preprocess_image(pil_image: Image.Image) -> Image.Image:
    """
    Aplica técnicas de pré-processamento para melhorar a qualidade da imagem para OCR.
    """
    # 1. Converter para Grayscale
    img = pil_image.convert("L")

    # 2. Aumento de Contraste e Brilho (Pillow)
    enhancer_contrast = ImageEnhance.Contrast(img)
    img = enhancer_contrast.enhance(1.5) # Aumenta o contraste em 50%
    enhancer_brightness = ImageEnhance.Brightness(img)
    img = enhancer_brightness.enhance(1.1) # Aumenta o brilho em 10%

    # 3. Binarização (Pillow ou OpenCV para mais controle)
    # Convertendo para NumPy array para usar OpenCV
    np_img = np.array(img)

    # Aplica um threshold adaptativo para binarização
    # Isso funciona bem para imagens com variações de iluminação
    # binary_img = cv2.adaptiveThreshold(np_img, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
    #                                   cv2.THRESH_BINARY, 11, 2)
    
    # Opcional: Remoção de Ruído (OpenCV) - Usar Denoising ou Bilateral Filter
    # Se a imagem tiver muito ruído (pixelado), isso pode ajudar
    denoised_img = cv2.fastNlMeansDenoising(np_img, None, 10, 7, 21) # Para imagens em grayscale
    binary_img = denoised_img

    # Opcional: Nitidez (OpenCV)
    # kernel = np.array([[-1,-1,-1], [-1,9,-1], [-1,-1,-1]])
    # sharpened_img = cv2.filter2D(binary_img, -1, kernel)
    # binary_img = sharpened_img

    # Retorna para PIL Image
    processed_pil_image = Image.fromarray(binary_img)

    return processed_pil_image

@tool
def processar_documento_ocr(file_path: str, prompt: str) -> Dict[str, Any]:
    """
    Processa um arquivo (imagem ou PDF) usando o modelo Gemini para OCR e extração de informações,
    com pré-processamento de imagem para melhorar a qualidade.

    Args:
        file_path: O caminho do arquivo local (ex: "comprovante.png" ou "nota_fiscal.pdf").
        prompt: O prompt para o Gemini, descrevendo o que deve ser extraído.
    Returns:
        Um dicionário contendo o texto extraído e/ou as informações estruturadas.
    """
    try:
        messages_to_send = [{"type": "text", "text": prompt}]
        processed_images_base64 = []

        if file_path.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.bmp', '.tiff')):
            with open(file_path, "rb") as f:
                pil_image = Image.open(f).convert("RGB") # Abrir como RGB antes do processamento
            
            processed_pil_image = preprocess_image(pil_image)
            
            img_byte_arr = io.BytesIO()
            processed_pil_image.save(img_byte_arr, format="JPEG")
            processed_images_base64.append(base64.b64encode(img_byte_arr.getvalue()).decode("utf-8"))

        elif file_path.lower().endswith('.pdf'):
            doc = fitz.open(file_path)
            for page_num in range(min(doc.page_count, 100)): # Limite para 3 páginas para fotos de baixa qualidade
                page = doc.load_page(page_num)
                pix = page.get_pixmap(matrix=fitz.Matrix(2, 2)) # Renderiza com DPI maior (2x) para melhor qualidade
                pil_image = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
                
                processed_pil_image = preprocess_image(pil_image)
                
                img_byte_arr = io.BytesIO()
                processed_pil_image.save(img_byte_arr, format="JPEG")
                processed_images_base64.append(base64.b64encode(img_byte_arr.getvalue()).decode("utf-8"))
            doc.close()
            
            if not processed_images_base64:
                return {"error": "Nenhuma imagem pôde ser extraída ou processada do PDF."}
        else:
            return {"error": "Formato de arquivo não suportado. Use .png, .jpg, .pdf, etc."}

        for img_b64 in processed_images_base64:
            messages_to_send.append({
                "type": "image_url",
                "image_url": {"url": f"data:image/jpeg;base64,{img_b64}"}
            })

        message = HumanMessage(content=messages_to_send)
        response = llm_genai.invoke([message])
        # print(response.content)
        extracted_content = response.content
        
        if "json" in prompt.lower():
            try:
                import json
                return json.loads(extracted_content)
            except json.JSONDecodeError:
                pass
        
        return extracted_content

    except Exception as e:
        return {"error": f"Erro ao processar documento com pré-processamento: {e}"}

@tool
def save_renegotiation(tax_id:str, operation_code: str, valor_divida: float, parcelas: str): 
    """Use esta ferramenta para salvar as informações de **renegociação** no banco de dados.
    De input, deve conter a Cédula de Crédito Bancário (operation_code), o valor total da dívida (valor_divida), quais parcelas foram renegociadas (parcelas) e o CPF ou CNPJ (tax_id) do usuário.
    Estes valores, exceto o tax_id, estão no tópico '1. DO OBJETO', traga no seguinte formato: operation_code = 'A9852213-000', valor_divida = 21305.00, parcelas = '12-22', tax_id = '89654785201'.
    """
    tax_id = re.sub('[\./-]', '', tax_id)
    conn = psycopg2.connect(dbname="postgres", user="postgres", password="1673", host=r"localhost")
    cur = conn.cursor()
    cur.execute(f"INSERT INTO renegotiations (tax_id, operation_code, valor_divida, parcelas) VALUES ('{tax_id}', '{operation_code}', {valor_divida}, '{parcelas}');")
    conn.commit()

@tool
def save_taxes(tax_id: str, rendimento: float, imposto_pago: float): 
    """Use esta ferramenta para salvar as informações de **imposto de renda** no banco de dados.
    De input, deve conter o TOTAL DE RENDIMENTOS TRIBUTÁVEIS (rendimento), o Total do imposto pago (imposto_pago) e o CPF ou CNPJ (tax_id) do usuário.
    Estes valores estão nas últimas páginas do documento, onde vai encontrar "RESUMO".
    Traga no seguinte formato: rendimento = 56214.12, imposto_pago = 3562.12, tax_id = '89654785201'.
    """
    tax_id = re.sub('[\./-]', '', tax_id)
    conn = psycopg2.connect(dbname="postgres", user="postgres", password="1673", host=r"localhost")
    cur = conn.cursor()
    cur.execute(f"INSERT INTO taxes (tax_id, rendimento, imposto_pago) VALUES ('{tax_id}', {rendimento}, {imposto_pago});")
    conn.commit()