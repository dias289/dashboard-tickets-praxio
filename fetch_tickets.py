import requests
import pandas as pd
import json
import os
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
    # Pega a página inicial para obter o cookie de sessão
    session.get(f"{BASE_URL}/Home/Index", timeout=30)
    # Faz o login com os campos corretos
    resp = session.post(
        f"{BASE_URL}/Home/Entrar",
        data={"txtLogin": EMAIL, "txtSenha": SENHA, "ReturnUrl": ""},
        timeout=30,
        allow_redirects=True,
    )
    logado = "Ticket" in resp.url or resp.url.endswith("/Ticket")
    print(f"URL apos login: {resp.url}")
    print(f"Status: {resp.status_code}")
    return logado


def download_xlsx(session):
    resp = session.get(EXPORT_URL, timeout=120)
    resp.raise_for_status()
    content = resp.content
    print(f"Content-Type: {resp.headers.get('Content-Type', '?')}")
    print(f"Tamanho: {len(content)} bytes")
    if b"<!DOCTYPE" in content[:100] or b"<html" in content[:100]:
        raise RuntimeError(f"Portal retornou HTML. Sessao expirou?\n{content[:300]}")
    return content


def process_data(xlsx_bytes):
    df = pd.read_excel(BytesIO(xlsx_bytes), header=1)
    df.columns = df.columns.str.strip()

    col_status = next(c for c in df.columns if "Status" in c)
    col_grupo  = next(c for c in df.columns if "Grupo" in c)
    col_resp   = next(c for c in df.columns if "Respons" in c)
    col_ticket = next(c for c in df.columns if "ticket" in c.lower() or "protocolo" in c.lower())

    valid = ["Em andamento", "Concluído", "Cancelado", "Pendente cliente", "Pendente Cliente"]
    df = df[df[col_status].isin(valid)].copy()
    df[col_status] = df[col_status].str.strip()
    df[col_grupo]  = df[col_grupo].fillna("Sem grupo").str.strip()
    df[col_resp]   = df[col_resp].fillna("Sem responsavel").str.strip()

    tickets_por_time = {str(k): int(v) for k, v in
        df.groupby(col_grupo)[col_ticket].count().sort_values(ascending=False).items()}

    em_andamento     = df[df[col_status] == "Em andamento"].copy()
    cancelados       = df[df[col_status] == "Cancelado"].copy()
    pendente_cliente = df[df[col_status].str.lower() == "pendente cliente"].copy()

    df_cons = df[df[col_status].isin(["Em andamento", "Concluído"])].copy()
    por_consultor = (
        df_cons.groupby([col_resp, col_status])[col_ticket]
        .count().unstack(fill_value=0).reset_index()
    )
    por_consultor.columns.name = None
    for s in ["Em andamento", "Concluído"]:
        if s not in por_consultor.columns:
            por_consultor[s] = 0
    por_consultor["Total"] = por_consultor["Em andamento"] + por_consultor["Concluído"]
    por_consultor = por_consultor.sort_values("Total", ascending=False)

    def to_rec(d):
        return json.loads(d.to_json(orient="records", force_ascii=False, date_format="iso"))

    return {
        "atualizado_em": datetime.now().strftime("%d/%m/%Y %H:%M"),
        "totais": {
            "total":            int(len(df)),
            "em_andamento":     int(len(em_andamento)),
            "cancelados":       int(len(cancelados)),
            "pendente_cliente": int(len(pendente_cliente)),
            "concluidos":       int(len(df[df[col_status] == "Concluído"])),
        },
        "tickets_por_time":  tickets_por_time,
        "em_andamento":      to_rec(em_andamento),
        "cancelados":        to_rec(cancelados),
        "pendente_cliente":  to_rec(pendente_cliente),
        "por_consultor":     to_rec(por_consultor),
        "col_names": {
            "status": col_status,
            "grupo":  col_grupo,
            "resp":   col_resp,
            "ticket": col_ticket,
        },
    }


def main():
    session = requests.Session()
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                      "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Referer": BASE_URL,
    })

    print("Fazendo login...")
    if not login(session):
        raise RuntimeError("Falha no login — verifique as credenciais.")
    print("Login OK")

    print("Baixando relatorio...")
    xlsx_bytes = download_xlsx(session)
    print(f"Arquivo recebido ({len(xlsx_bytes):,} bytes)")

    print("Processando dados...")
    data = process_data(xlsx_bytes)
    print(f"{data['totais']['total']} tickets processados")

    os.makedirs("data", exist_ok=True)
    with open("data/tickets.json", "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"Salvo. Atualizado em: {data['atualizado_em']}")


if __name__ == "__main__":
    main()
