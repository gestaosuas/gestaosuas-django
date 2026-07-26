---
name: vps-deploy
description: Deploy Gestaosuas-django to the production VPS (Tailscale, 100.76.30.36) via SSH and verify it landed correctly. Use whenever asked to "atualizar a vps", "dar deploy", or ship committed changes to production.
---

# Deploy para a VPS de produção (Gestaosuas-django)

Contexto completo (credenciais, arquitetura da VPS, histórico de incidentes) está em `CLAUDE.md`, seção "VPS Produção" — leia lá antes se for a primeira vez na sessão. Esta skill é o procedimento operacional seguro pra executar o deploy sem repetir os incidentes já sofridos.

## Pré-requisito

Só faça deploy depois que o código já estiver commitado **e** `git push`ado pro `origin/master` — nunca faça deploy de uma branch/estado que não está no GitHub, porque `atualizar.sh` faz `git pull` no repo da VPS.

## Passo 1 — Credenciais SSH

`VPS_SSH_USER`/`VPS_SSH_PASSWORD` ficam em `.env.local` (raiz do repo, gitignored). **A senha salva ali fica desatualizada com frequência** (já aconteceu pelo menos 2x) — antes de assumir que vai funcionar, ou já tente com uma senha recém-confirmada pelo usuário na mesma sessão, ou teste uma vez e trate falha de autenticação como esperado, não como bug.

Se a autenticação falhar: **não fique retentando** (risco de acionar fail2ban na VPS). Pare e pergunte ao usuário a senha atual, oferecendo como opção recomendada a última senha confirmada verbalmente na sessão (se houver uma).

## Passo 2 — Rodar `atualizar.sh` com o padrão seguro

**Nunca** rode `./atualizar.sh` (ou qualquer `docker compose up -d --build`) via um script SSH que imprime a saída direto no console. Um `UnicodeEncodeError` do console Windows já matou o processo local no meio de um `docker compose up --build` remoto, deixando o container antigo "Exited" e um container órfão com nome mangled (`<hash>_gestaosuas_app`) no lugar do `gestaosuas_app` de verdade.

Sempre escreva a saída remota **num arquivo**, nunca em `print()` direto:

```python
import os
import paramiko

HOST = "100.76.30.36"
USER = os.environ["VPS_SSH_USER"]
PASSWORD = os.environ["VPS_SSH_PASSWORD"]

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect(HOST, username=USER, password=PASSWORD, timeout=20)

cmd = "cd /DATA/AppData/Gestaosuas-django && ./atualizar.sh"
stdin, stdout, stderr = client.exec_command(cmd, get_pty=True, timeout=600)

out_path = "<scratchpad>/vps_deploy_output.txt"  # caminho no scratchpad da sessão
with open(out_path, "w", encoding="utf-8") as f:
    for line in iter(stdout.readline, ""):
        f.write(line)
        f.flush()

exit_status = stdout.channel.recv_exit_status()
with open(out_path, "a", encoding="utf-8") as f:
    f.write(f"\n=== EXIT STATUS: {exit_status} ===\n")
client.close()
print("done, exit status:", exit_status)
```

Rode esse script via Bash/PowerShell com `VPS_SSH_USER`/`VPS_SSH_PASSWORD` exportados no ambiente (nunca hardcoded no arquivo). Timeout generoso (300–600s) — o build+restart de containers pode levar alguns minutos.

Depois, **leia o arquivo de saída** (`Read` tool) e confira:
- `[3/5] Baixando atualizações do GitHub...` terminou no commit esperado (`HEAD is now at <hash> <mensagem>`)
- `[4/5] Aplicando alterações de schema pendentes...` rodou sem erro (se `scripts/pending_alters.sql` tiver algo pendente)
- `[5/5]` terminou com `Containers reiniciados.` e `Atualização concluída com sucesso!`
- `=== EXIT STATUS: 0 ===` no final

Se o script falhar num passo intermediário, **não tente rodar de novo automaticamente** — leia o erro exato primeiro (pode ser o gotcha de `DOCKER_CONFIG=/tmp/dockercfg` se for um `docker compose` direto fora do `atualizar.sh`, que já exporta isso).

## Passo 3 — Verificar que o deploy pegou de verdade

Depois do `atualizar.sh` terminar, rode uma segunda checagem (mesmo padrão de saída-pra-arquivo) confirmando:

```bash
cd /DATA/AppData/Gestaosuas-django && git log --oneline -1
docker ps --filter name=gestaosuas --format 'table {{.Names}}\t{{.Status}}'
curl -s -o /dev/null -w 'HTTP_STATUS=%{http_code}\n' https://servidor-qualificacao.tailbeb7d5.ts.net:8443/ -k
```

Confirme:
1. O commit no `git log` bate com o que você acabou de dar push.
2. `docker ps` mostra `gestaosuas_app` (nome exato, **não** um nome com hash prefixado — isso indicaria o incidente de container órfão descrito acima) e `gestaosuas_db`, ambos "Up"/"Healthy".
3. `HTTP_STATUS=302` (redirect pro login — comportamento normal de app funcionando) na URL pública.

Se o nome do container vier mangled (`<hash>_gestaosuas_app`) em vez de `gestaosuas_app`: `docker rm -f <nome_orfao> gestaosuas_app` seguido de `docker compose -f docker-compose.yml up -d --build` limpo (com `DOCKER_CONFIG=/tmp/dockercfg` exportado).

## Depois de um `ALTER TABLE` em dev

Antes mesmo de chegar nesta skill: se a mudança que você está deployando incluiu uma `ALTER TABLE` feita em dev, ela **precisa** já estar em `scripts/pending_alters.sql` (idempotente, `ADD COLUMN IF NOT EXISTS`) — o passo `[4/5]` do `atualizar.sh` aplica esse arquivo automaticamente. Sem isso, a VPS quebra com 500 de coluna inexistente assim que o código novo tentar usar o campo. Ver CLAUDE.md, seção "Banco de Dados".

## Nunca fazer sem pedido explícito do usuário

- `git push --force`
- Rodar `docker compose` de produção em paralelo ao dev na mesma máquina (conflito de porta 8080)
- Resetar rotas do `tailscale serve`/`funnel` sem checar `tailscale serve status` antes e reaplicar tudo depois
- Restaurar/sobrescrever o banco de produção
