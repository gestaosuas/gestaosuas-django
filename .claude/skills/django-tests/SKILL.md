---
name: django-tests
description: Run the Django test suite for Gestaosuas-django correctly and interpret failures. Use before considering any bug fix or feature "verified", and whenever asked to run tests.
---

# Rodando a suíte de testes (Gestaosuas-django)

## Por que isso não é um `manage.py test` normal

Quase todo model de negócio deste projeto tem `managed = False` (schema gerenciado manualmente no Postgres, fora do controle de migrations do Django — ver `CLAUDE.md`, seção "Banco de Dados"). Isso quebra o comportamento padrão do test runner do Django, que cria um banco de testes vazio e roda migrations nele: as migrations desses apps não emitem `CREATE TABLE`, então o banco de testes vazio nunca teria as tabelas de negócio.

A correção já está em `config/settings.py` (`DATABASES["default"]["TEST"]["NAME"]` aponta pro próprio banco de dev) — isso faz o "banco de testes" ser o banco de dev real. É seguro porque `TestCase` (nunca `TransactionTestCase`) envolve cada teste numa transação com rollback automático: nada é persistido de fato.

## Comando correto

```sh
DB_HOST=127.0.0.1 DB_PORT=5433 python manage.py test <app_ou_caminho> --keepdb -v 2
```

Regras não-negociáveis:
- **Sempre `--keepdb`**. Sem essa flag o Django tenta criar/destruir um banco de testes de verdade — não é isso que você quer aqui.
- **Sempre `DB_HOST=127.0.0.1 DB_PORT=5433`** (a porta do Postgres do container dev exposta no host). Nunca rode contra qualquer coisa que possa ser o banco de produção.
- Rode direto no host (fora do Docker) pra iterar rápido — o container dev não tem hot-reload de código, então testar dentro dele exigiria rebuild a cada mudança.

## Rodando múltiplos apps de uma vez

Passar vários labels de app na mesma chamada (`manage.py test apps.a apps.b apps.c`) já deu `TypeError` na descoberta de testes pra certas combinações neste projeto (app sem `tests.py` tratado como pacote sem `__init__.py`/módulo). Se isso acontecer, rode os apps **um de cada vez** num loop, em vez de tentar depurar a descoberta de testes do runner:

```sh
for app in apps.directorates apps.monitoramento apps.accounts; do
  echo "=== $app ==="
  DB_HOST=127.0.0.1 DB_PORT=5433 python manage.py test $app --keepdb -v 1
done
```

## Escrevendo testes novos neste projeto

- `django.test.TestCase`, nunca `TransactionTestCase` (perderia o isolamento por rollback contra o banco real).
- Nunca crie/edite/apague linhas de tabelas "singleton" compartilhadas (`directorates`, `settings`) — leia registros existentes (`Directorate.objects.first()` etc.) ou crie registros com identificadores únicos por teste (sufixo `uuid.uuid4().hex[:8]` no nome, por exemplo).
- Se o teste cria uma `Directorate` com um nome "temático" (ex. algo contendo "Subvenção", "CRAS", "Emendas") pra exercitar lógica que detecta o tipo de diretoria pelo nome, **sempre** adicione um sufixo único (`f"Subvenção Teste {uuid.uuid4().hex[:8]}"`) — um nome literal como `"Subvenção"` pode colidir com o slug de uma `Directorate` real já existente no banco de dev (usado por `DirectorateSlugConverter`), causando resolução de URL ambígua e falhas confusas (`response redirected to '/'` em vez do esperado).
- Ao criar dados relacionados via `Model.objects.create()` direto (sem passar por uma view), confira se todos os campos `NOT NULL` do banco real estão sendo passados — o estado real do schema (`managed=False`) pode divergir do que a definição do model sugere como opcional (ex.: `FormDelegation.delegated_by` é `NOT NULL` no banco de dev mesmo não estando marcado assim no model/migration).

## Quando um teste falha: descubra se você causou isso

Antes de tentar "consertar" um teste que falhou, confirme se a falha é **pré-existente** (não relacionada à sua mudança) ou se você a introduziu:

```sh
git stash
DB_HOST=127.0.0.1 DB_PORT=5433 python manage.py test <caminho.do.teste.especifico> --keepdb -v 1
git stash pop
```

Se a mesma falha aparece sem a sua mudança, é débito técnico pré-existente — não é sua responsabilidade corrigir agora (mas vale mencionar ao usuário, sem misturar no commit atual). Se só falha COM sua mudança, é uma regressão real que você precisa investigar e corrigir antes de considerar o trabalho pronto.
