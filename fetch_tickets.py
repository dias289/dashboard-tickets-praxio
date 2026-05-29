import requests
import pandas as pd
import json
import os
import re
from datetime import datetime
from io import BytesIO

EMAIL = os.environ["PORTAL_EMAIL"]
SENHA = os.environ["PORTAL_SENHA"]

BASE_URL = "https://portaldocliente.praxio.com.br"
EXPORT_URL = (
    f"{BASE_URL}/Ticket/ExportTo?tipo=2&configsGrid="
    "[[%22Protocolo%22,true,2,87.090909],[%22AssuntoPesquisa%22,true,3,382.090909],"
    "[%22DataHoraPrevisaoAtendimento%22,true,7,70.090909],[%22Nivel%22,true,10,96.090909],"
    "[%22Status%22,true,4,135.090909],[%22Origem%22,true,5,84.090909],"
    "[%22DataHoraAbertura%22,true,6,160.090909],[%22NomeCliente%22,true,9,250.090909],"
    "[%22BusinessUnit%22,true,19,150.090909],[%22CodigoSistema%22,false,13,80],"
    "[%22CodigoModulo%22,true,11,103.090909],[%22NomeOperadorContato%22,true,12,205.090909],"
    "[%22QuantidadeTramites%22,false,18,110],[%22NomeOperadorResponsavel%22,true,13,150.090909],"
    "[%22DataHoraTramite%22,true,8,180.090909],[%22DataHoraConclusao%22,true,15,155.090909],"
    "[%22Sinalizador%22,true,0,54.090908999999996],[%22Natureza%22,true,1,82.090909],"
    "[%22DataProximaAcao%22,false,20,140],[%22IdGrupoAtendimento%22,true,14,150.090909],"
    "[%22Anexo%22,false,21,80],[%22CurvaAbc%22,false,23,80],[%22AvaliacaoCliente%22,false,24,80],"
    "[%22GlobusCloud%22,false,25,85],[%22ClienteCritico%22,false,26,90],"
    "[%22ClienteVip%22,false,27,80],[%22AtendeUsuarioChave%22,false,31,150],"
    "[%22GrupoTipo%22,true,16,105.090909],[%22TempoContrato%22,true,18,150.090909],"
    "[%22Adequa%C3%A7%C3%B5es%22,true,17,160.090909],[%22DataPrevistaEntrega%22,false,33,155],"
    "[%22RespostaIA%22,true,34,80]]&ordemGrid=[]"
)


def login(session):
    # Busca a página de login para obter cookie de sessão e token CSRF
    resp = session.get(f"{BASE_URL}/Home/Index", timeout=30)
    print(f"GET Index status: {resp.status_code}")
    print(f"Cookies apos GET: {dict(session.cookies)}")
    
    # Procura todos os hidden inputs no formulário
    hidden_fields = re.findall(r'<input[^>]+type=["\']hidden["\'][^>]*>', resp.text, re.IGNORECASE)
    print(f"Hidden fields encontrados: {hidden_fields}")
    
    # Procura especificamente o form de login
    form_match = re.search(r'<form[^>]*action[^>]*Entrar[^>]*>(.*?)</form>', resp.text, re.DOTALL | re.IGNORECASE)
    if form_match:
        print(f"Form encontrado: {form_match.group(0)[:500]}")
    else:
        print("Form de login NAO encontrado na pagina Index")
        # Tenta a pagina de login diretamente
        resp2 = session.get(f"{BASE_URL}/Home/Login", timeout=30)
        print(f"GET Login status: {resp2.status_code}")
        form_match2 = re.search(r'<form[^>]*>(.*?)</form>', resp2.text, re.DOTALL | re.IGNORECASE)
        if form_match2:
            print(f"Form em /Login: {form_match2.group(0)[:500]}")

    return False  # Por agora só diagnóstico


def main():
    session = requests.Session()
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                      "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Referer": BASE_URL,
    })
    print("Diagnosticando login...")
    login(session)


if __name__ == "__main__":
    main()
