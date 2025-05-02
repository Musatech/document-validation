import csv
import json

import pymupdf
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# If modifying these scopes, delete the file token.json.
SCOPES = ["https://www.googleapis.com/auth/drive.readonly"]

SERVICE_ACCOUNT_FILE = 'data-457718-907d56676c82.json'

ORIGENS = {
    '1eVZZC8I6W-joaXFlE4ovMDLCXdPdNIm0': {
        'nome': 'ZAMP - Óleo',
        'tipo': 'transportador',
    },
    '1Tg845zCTeWTlKqITMYGpVJ_MzybbFCv9': {
        'nome': 'Zamp - Óleo e RSU',
        'tipo': 'transportador',
    },
    '1j8d9to9snLECREjVsIkxRY-C01C_upK9': {
        'nome': 'Zamp - RSU',
        'tipo': 'transportador',
    },
    # '1F3a2rMpEg2UCRbwl7FmHAORkePxq_Apq': {
    #     'nome': 'BSB',
    # },
    '1J7_58uk-6LGDnNV9TAponZZTiahnqWVB': {
        'nome': '2. Transportadoras (Documentação)',
        'tipo': 'transportador',
    },
    '1FMm9itnd8jE0Pd56WTfMh4DlFZZn9LCv': {
        'nome': '4. Receptoras',
        'tipo': 'receptor',
    },
}

CHECKLISTS = {
    'transportador': {
        'preliminares': [
            'Contrato Social',
            'CNPJ',
            'Licença de Operação',
            'AVCB',
            'Cadastro em plataforma para emissão de MTR',
            'CND',
        ],
        'complementares': [
            'CTF AIDA',
            'CTF APP',
            'Cópia da CNH dos motoristas',
            'Documento de veículos utilizados na coleta',
            'Contrato com a Musa',
        ],
    },
    'receptor': {
        'preliminares': [
            'Contrato Social',
            'Cartão CNPJ',
            'Alvará de funcionamento',
            'AVCB',
            'Cadastro em plataforma para emissão de MTR',
            'CND',
        ],
        'complementares': [
            'CTF AIDA',
            'CTF APP',
        ],
    },
    'aterro_sanitario': [
        'Licença de Instalação',
    ]
}

PARCEIRO_ESTADO = {
    'Verdes Óleos': 'SP',
    'Óleo Verde': 'MG',
    'Preserve Ambiental': '',	
    'Giglio': 'SP',
    'Green Oil': 'SP',
    'MGA': '',
    'Grupo Hávila + Retioleo': 'SP',
    'Guará Óleo Vale': 'SP',
    'Power Transporte': 'RJ',
    'Indama': 'MA',
    'Estre': 'PR',	
    'Prevencar': 'AL',
    'Róleo': 'MG',
    'Pro Ambiental': 'MG',
    'Bioquim': 'RS',
    'CROU': '',
    'Agit': '',
    'Terra Viva': 'MG',
    'Sol Ambiental': 'MS',
    'Bio Reciclagem de Óleo Vegetal': 'DF',
    'Lírium': 'SP',
    'Ecóleo': 'ES',
    'Recóleo': 'MG',
    'Kurica': '',
    'Zero Resíduos': '',
    'Resquin': '',
    'Grupo Urbam': 'RJ',
    'Coleturb/SUPRA': 'RS',
    'GTR': 'PE',
}

ESTADO_CONFIGURACAO_DOCUMENTO = {
    'SP': {
        'Licença de Operação': {
            'valido_ate': {
                'page_number': 0,
                'coordinates': (310, 110, 440, 120),
            },
            'orgao_ambiental': {
                'page_number': 0,
                'coordinates': (50, 50, 440, 60),
            },
        }
    },
    # 'MG': {
    #     'AVCB': {
    #         'valido_ate': {
    #             'page_number': 0,
    #             'coordinates': (),
    #         }
    #     }
    # },
    'MA': {
        'Licença de Operação': {
            'valido_ate': {
                'page_number': 0,
                'coordinates': (400, 200, 550, 230),
            },
            'orgao_ambiental': {
                'page_number': 0,
                'coordinates': (0, 130, 600, 150),
            }
        }
    }
}

class GoogleDrive:
    def __init__(self):
        self._authenticate()

    def _authenticate(self):
        try:
            creds = Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes=SCOPES)
            self.service = build("drive", "v3", credentials=creds)
        except Exception as e:
            print(f"Erro ao carregar credenciais da Service Account: {e}")
            print(f"Certifique-se de que o arquivo '{SERVICE_ACCOUNT_FILE}' existe e é válido.")

    def list_files(self, query=None):
        output = []
        page_token = None
        try:
            while True:
                results = (
                    self.service.files()
                    .list(
                        q=query,
                        pageSize=1000,
                        fields="nextPageToken, files(id, name, parents, mimeType)"
                    )
                    .execute()
                )
                output.extend(results.get("files", []))
                page_token = results.get('nextPageToken', None)
                if page_token is None:
                    break
            
            return output

        except HttpError as error:
            print(f"Ocorreu um erro da API do Drive: {error}")
            raise
        except Exception as e:
            print(f"Ocorreu um erro inesperado: {e}")
            raise

    def download_file(self, file_id):
        try:
            return (
                self.service.files()
                .get_media(fileId=file_id)
                .execute()
            )
        except HttpError as error:
            print(f"Ocorreu um erro da API do Drive: {error}")
            raise
        except Exception as e:
            print(f"Ocorreu um erro inesperado: {e}")
            raise


def is_string_in_dict_values(input_string, input_dict):
    matches = []
    for key, value in input_dict.items():
        if input_string.lower() in value.lower():
            matches.append((key, value))
    
    for key, value in matches:
        del input_dict[key]
    
    return matches


def find_text_in_document(file_content, page_number=None, coordinates=None):
    with pymupdf.open(stream=file_content) as doc:
        page = doc.load_page(page_number)
        region_rect = pymupdf.Rect(*coordinates) if coordinates else None
        text = page.get_text('text', clip=region_rect).strip()
    return text


def main():
    googledrive = GoogleDrive()

    query = ' or '.join(f"'{origem_id}' in parents" for origem_id in ORIGENS.keys())
    pastas = {
        pasta['id']: {
            'parceiro': pasta['name'],
            'link_pasta': f'https://drive.google.com/drive/folders/{pasta['id']}',
            'origem': ORIGENS[pasta['parents'][0]]['nome'],
            'tipo': ORIGENS[pasta['parents'][0]]['tipo']
        }
        for pasta in googledrive.list_files(f"({query}) and trashed = false")
    }
    print(f"Total de pastas encontrados pela API: {len(pastas)}")

    if len(pastas) == 0:
        return

    query = ' or '.join(f"'{pasta_id}' in parents" for pasta_id in pastas.keys())
    arquivos = googledrive.list_files(f"({query}) and trashed = false")
    print(f"Total de arquivos encontrados pela API: {len(arquivos)}")

    resultados = []
    repescagem = []

    for arquivo in arquivos:
        parent_id = arquivo['parents'][0]
        if 'arquivos' not in pastas[parent_id]:
            pastas[parent_id]['arquivos'] = {}

        if arquivo.get('mimeType') == 'application/vnd.google-apps.folder':
            repescagem.append({
                'parceiro': pastas[parent_id]['parceiro'],
                'link_pasta': pastas[parent_id]['link_pasta'],
                'origem': pastas[parent_id]['origem'],
                'nome': arquivo['name'],
                'url': f'https://drive.google.com/drive/folders/{arquivo['id']}',
            })
        else:
            pastas[parent_id]['arquivos'][arquivo['id']] = arquivo['name']
    
    with open('repescagem.json', 'w', encoding='utf-8') as f:
        json.dump(repescagem, f, indent=2, ensure_ascii=False)

    for pasta in pastas.values():
        pasta['checklist'] = []
        checklist = [
            {
                'item_checklist': item,
                'categoria': 'preliminares',
            }
            for item in CHECKLISTS[pasta['tipo']]['preliminares']
        ] + [
            {
                'item_checklist': item,
                'categoria': 'complementares',
            }
            for item in CHECKLISTS[pasta['tipo']]['complementares']
        ]

        for item in checklist:
            matches = is_string_in_dict_values(item['item_checklist'], pasta.get('arquivos', {}))

            if matches:
                for arquivo_id, arquivo_nome in matches:
                    valido_ate = None
                    orgao_ambiental = None

                    estado = PARCEIRO_ESTADO.get(pasta['parceiro'])
                    if estado and estado in ESTADO_CONFIGURACAO_DOCUMENTO:
                        document_config = ESTADO_CONFIGURACAO_DOCUMENTO[estado].get(item['item_checklist'])

                        if document_config:
                            file_content = googledrive.download_file(arquivo_id)

                            valido_ate = find_text_in_document(file_content, **document_config['valido_ate']) if 'valido_ate' in document_config else None
                            orgao_ambiental = find_text_in_document(file_content, **document_config['orgao_ambiental']) if 'orgao_ambiental' in document_config else None

                    pasta['checklist'].append({
                        'item_checklist': item['item_checklist'],
                        'categoria': item['categoria'],
                        'encontrado?': True,
                        'nome_arquivo': arquivo_nome,
                        'link_arquivo': f'https://drive.google.com/file/d/{arquivo_id}/view?usp=drive_link',
                        'valido_ate': valido_ate,
                        'orgao_ambiental': orgao_ambiental,
                    })

                    resultados.append({
                        'parceiro': pasta['parceiro'],
                        'link_pasta': pasta['link_pasta'],
                        'origem': pasta['origem'],
                        'tipo': pasta['tipo'],
                        'item_checklist': item['item_checklist'],
                        'categoria': item['categoria'],
                        'encontrado?': True,
                        'nome_arquivo': arquivo_nome,
                        'link_arquivo': f'https://drive.google.com/file/d/{arquivo_id}/view?usp=drive_link',
                        'valido_ate': valido_ate,
                        'orgao_ambiental': orgao_ambiental,
                    })
            else:
                pasta['checklist'].append({
                    'item_checklist': item['item_checklist'],
                    'categoria': item['categoria'],
                    'encontrado?': False,
                    'nome_arquivo': None,
                    'link_arquivo': None,
                    'valido_ate': None,
                    'orgao_ambiental': None,
                })

                resultados.append({
                    'parceiro': pasta['parceiro'],
                    'link_pasta': pasta['link_pasta'],
                    'origem': pasta['origem'],
                    'tipo': pasta['tipo'],
                    'item_checklist': item['item_checklist'],
                    'categoria': item['categoria'],
                    'encontrado?': False,
                    'nome_arquivo': None,
                    'link_arquivo': None,
                    'valido_ate': None,
                    'orgao_ambiental': None,
                })

        for arquivo_id, arquivo_nome in pasta.get('arquivos', {}).items():
            pasta['checklist'].append({
                'item_checklist': None,
                'categoria': None,
                'encontrado?': False,
                'nome_arquivo': arquivo_nome,
                'link_arquivo': f'https://drive.google.com/file/d/{arquivo_id}/view?usp=drive_link',
                'valido_ate': None,
                'orgao_ambiental': None,
            })

            resultados.append({
                'parceiro': pasta['parceiro'],
                'link_pasta': pasta['link_pasta'],
                'origem': pasta['origem'],
                'tipo': pasta['tipo'],
                'item_checklist': None,
                'categoria': None,
                'encontrado?': False,
                'nome_arquivo': arquivo_nome,
                'link_arquivo': f'https://drive.google.com/file/d/{arquivo_id}/view?usp=drive_link',
                'valido_ate': None,
                'orgao_ambiental': None,
            })


    with open('arquivos.json', 'w', encoding='utf-8') as f:
        json.dump(pastas, f, indent=2, ensure_ascii=False)
    
    with open('arquivos.csv', 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=['parceiro', 'link_pasta', 'origem', 'tipo', 'item_checklist', 'categoria', 'encontrado?', 'nome_arquivo', 'link_arquivo', 'valido_ate', 'orgao_ambiental'])
        writer.writeheader()

        for row in resultados:
            writer.writerow(row)


if __name__ == "__main__":
    main()

    # import os
    # file_id = '1JDsdlAJ5TXQJdHGksqeNI_OAscIFqifg'
    # page_number = 0
    # coordinates = (50, 50, 440, 60),

    # if not os.path.exists(f'documents/{file_id}.pdf'):
    #     googledrive = GoogleDrive()
    #     file_content = googledrive.download_file(file_id)

    #     with open(f'documents/{file_id}.pdf', 'wb') as f:
    #         f.write(file_content)

    # with pymupdf.open(f'documents/{file_id}.pdf') as doc:
    #     page = doc.load_page(page_number)
    #     print(page.rect.width, page.rect.height)
    #     region_rect = pymupdf.Rect(*coordinates) if coordinates else None
    #     text = page.get_text('text', clip=region_rect).strip()

    # print(text)
