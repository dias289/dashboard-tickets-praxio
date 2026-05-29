import json
import os
import time
from datetime import datetime
from io import BytesIO
import pandas as pd

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

def get_xlsx_via_selenium():
    from selenium import webdriver
    from selenium.webdriver.common.by import By
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    import requests

    download_dir = os.path.abspath("downloads")
    os.makedirs(download_dir, exist_ok=True)

    options = Options()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920,1080")
    options.add_experimental_option("prefs", {
        "download.default_directory": download_dir,
        "download.prompt_for_download": False,
    })

    driver = webdriver.Chrome(options=options)
    wait = WebDriverWait(driver, 30)

    try:
        print("Abrindo pagina de login...")
        driver.get(f"{BASE_URL}/Home/Index")
        time.sleep(2)

        print("Preenchendo credenciais...")
        wait.until(EC.presence_of_element_located((By.ID, "txtLogin")))
        driver.find_element(By.ID, "txtLogin").send_keys(EMAIL)
        driver.find_element(By.ID, "txtSenha").send_keys(SENHA)
        driver.find_element(By.CSS_SELECTOR, "button[type=submit], input[type=submit]").click()

        print("Aguardando redirect apos login...")
        wait.until(EC.url_contains("/Ticket"))
        print(f"Logado! URL: {driver.current_url}")

        # Pega os cookies do Selenium e usa no requests
        cookies = {c["name"]: c["value"] for c in driver.get_cookies()}
        print(f"Cookies obtidos: {list(cookies.keys())}")

        # Usa requests com os cookies do Selenium para baixar o xlsx
        import requests as req
        session = req.Session()
        session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                          "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        })
        for name, value in cookies.items():
            session.cookies.set(name, value)

        print("Baixando xlsx via requests com cookies do Selenium...")
        resp = session.get(EXPORT_URL, timeout=120)
        print(f"Content-Type: {resp.headers.get('Content-Type','?')}")
        print(f"Tamanho: {len(resp.content)} bytes")

        if b"<!DOCTYPE" in resp.content[:100]:
            raise RuntimeError("Ainda retornou HTML mesmo com cookies do Selenium")

        return resp.content

    finally:
        driver.quit()


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
            "status": col_status, "grupo": col_grupo,
            "resp": col_resp, "ticket": col_ticket,
        },
    }


def main():
    print("Iniciando coleta via Selenium...")
    xlsx_bytes = get_xlsx_via_selenium()
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
