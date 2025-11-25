import requests
import json
import pandas as pd

from ..core.config import ACCESS_TOKEN_CRM, ACCESS_TOKEN_CRM_FILE, URL_CRM

def get_file_data(file_id):
    '''Buscar arquivo no HubSpot e retornar como DataFrame'''

    try:
        # Buscar informações (URL) do arquivo de renegociação
        url_signed = f"https://api.hubapi.com/files/v3/files/{file_id}/signed-url"
        headers = {
            "Authorization": f"Bearer {ACCESS_TOKEN_CRM_FILE}"
        }

        response = requests.get(url_signed, headers=headers)

        resp = json.loads(response.content)
        url_file = resp['url']

        # Baixar o arquivo de renegociação
        resp_file = requests.get(url_file, headers=headers)

        return resp_file.content
        
    except requests.exceptions.RequestException as e:
        print(f"❌ Erro na requisição HTTP: {e}")
        raise

def save_ocr_data(extracted_content, deal_id):
    '''Salvar no CRM os dados extraídos do OCR'''

    url = URL_CRM + f"{deal_id}"

    headers = {
        "Authorization": f"Bearer {ACCESS_TOKEN_CRM}",
        "Content-Type": "application/json"
    }

    properties = {
        "properties": {
            "resumo_da_comprovacao_de_renda____ocr": extracted_content
        }
    }

    response = requests.patch(url, headers=headers, json=properties)

    return response

def save_crm_data(doc_model: dict, scr_n_autorizado: bool):
    '''Save data in CRM'''

    url = URL_CRM + f"{doc_model['dealId']}"

    headers = {
        "Authorization": f"Bearer {ACCESS_TOKEN_CRM}",
        "Content-Type": "application/json"
    }

    dict_reasons = doc_model['analysis']

    list_reasons = []
    for r in dict_reasons:
        if dict_reasons[r] == 'Reprovado':
            list_reasons.append(r)

    reasons_str = ', '.join(list_reasons)

    properties = {
        "properties": {
            "motivo_de_reprovacao_motor": reasons_str,
            "limite_pre_aprovado____motor_app": doc_model['creditLimit'],
            "taxa_de_juros_aprovada_pelo_motor_app": doc_model['rate'],
            "status_motor": doc_model['result'],
            "data_de_expiracao_da_proposta__app_": str(doc_model['expirationDate'].date()),
            "rating_agrisk": doc_model['ratingAgrisk'],
            "score_agrisk": doc_model['scoreAgrisk'],
            "rating_nagro_4_0": doc_model['ratingNagroV4'],
            "score_nagro_4_0": doc_model['scoreNagroV4'],
            "possui_autorizacao_scr_": scr_n_autorizado
        }
    }

    response = requests.patch(url, headers=headers, json=properties)

    return response