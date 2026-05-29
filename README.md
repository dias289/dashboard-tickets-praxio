# Dashboard de Tickets — Praxio

Dashboard automatizado que busca tickets do Portal do Cliente Praxio e exibe em tempo real.

## Estrutura

```
├── index.html          # Dashboard visual
├── fetch_tickets.py    # Script que baixa e processa os dados
├── data/
│   └── tickets.json    # Dados gerados automaticamente
└── .github/
    └── workflows/
        └── update.yml  # Agendamento automático (GitHub Actions)
```

---

## Configuração (passo a passo)

### 1. Criar o repositório no GitHub

1. Acesse [github.com](https://github.com) e clique em **New repository**
2. Nome sugerido: `dashboard-tickets-praxio`
3. Deixe como **Public** (necessário para GitHub Pages gratuito)
4. Clique em **Create repository**

### 2. Enviar os arquivos

No terminal (ou GitHub Desktop):

```bash
git init
git add .
git commit -m "feat: dashboard inicial"
git branch -M main
git remote add origin https://github.com/SEU_USUARIO/dashboard-tickets-praxio.git
git push -u origin main
```

### 3. Configurar as credenciais (Secrets)

> ⚠️ **Nunca coloque usuário e senha diretamente no código.**

1. No repositório, vá em **Settings → Secrets and variables → Actions**
2. Clique em **New repository secret** e adicione:
   - `PORTAL_EMAIL` → seu e-mail de login (ex: `felipe.dias@suaempresa.com.br`)
   - `PORTAL_SENHA`  → sua senha

### 4. Ativar o GitHub Pages

1. Vá em **Settings → Pages**
2. Em **Source**, selecione **Deploy from a branch**
3. Branch: `main` / pasta: `/ (root)`
4. Clique em **Save**
5. Aguarde ~1 minuto e acesse: `https://SEU_USUARIO.github.io/dashboard-tickets-praxio/`

### 5. Rodar manualmente pela primeira vez

1. Vá em **Actions** no repositório
2. Clique em **Atualizar Dashboard de Tickets**
3. Clique em **Run workflow → Run workflow**
4. Aguarde concluir (~1 minuto) e atualize o dashboard

---

## Frequência de atualização

O script roda automaticamente **a cada hora**, de segunda a sexta, das 7h às 20h (horário de Brasília).

Para alterar, edite o `cron` em `.github/workflows/update.yml`:

```yaml
- cron: "0 10-23 * * 1-5"   # hora UTC (Brasília = UTC-3)
```

---

## Solução de problemas

| Problema | Solução |
|---|---|
| Actions falha com erro de login | Verifique os Secrets `PORTAL_EMAIL` e `PORTAL_SENHA` |
| Dashboard não atualiza | Rode manualmente em Actions → Run workflow |
| Grupos de atendimento com nomes errados | Verifique a coluna `Grupo de Atendimento` no portal e ajuste o script |
