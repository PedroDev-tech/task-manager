# Task Manager

Aplicação web de gerenciamento de tarefas construída com **Flask** e **Flask-SQLAlchemy**. Permite criar, editar, listar, filtrar, ordenar, concluir e excluir tarefas, com prioridade, prazo, **etiquetas (tags)**, **anexos**, **API REST JSON**, **lembretes** e **notificações por e-mail** de tarefas atrasadas — com interface em Português/Inglês e tema claro/escuro.

## Funcionalidades

- **CRUD de tarefas** — criar, listar, editar e excluir.
- **Prioridade** (`alta`, `media`, `baixa`) e **prazo** (`due_date`).
- **Concluir/reabrir** com um clique (`/toggle/<id>`).
- **Etiquetas/categorias** — múltiplas tags por tarefa e filtro por tag.
- **Anexos** — upload múltiplo, download e remoção de arquivos.
- **Busca** por título ou descrição.
- **Filtros** por status (todas, pendentes, concluídas, atrasadas, hoje), prioridade e tag.
- **Ordenação** por mais recente, prazo ou prioridade.
- **Paginação** (8 itens por página).
- **Dashboard de estatísticas** (total, pendentes, concluídas, atrasadas) em consulta agregada única.
- **Indicadores visuais** de tarefas atrasadas e com prazo para hoje.
- **Lembretes** de tarefas próximas do vencimento e atrasadas (`/reminders`).
- **Notificações por e-mail** de tarefas atrasadas (`/notify/overdue`), via console ou SMTP.
- **API REST (JSON)** com CRUD completo.
- **Internacionalização** Português/Inglês (i18n próprio, sem dependências extras).
- **Tema claro/escuro** e **sidebar colapsável**, com preferência salva no navegador.
- **Acessibilidade** — skip link, foco visível, ARIA e mensagens de feedback (flash).
- **Apresentação** do projeto em slides (reveal.js) — veja `slides.html`.

## Tecnologias

- Python 3
- [Flask](https://palletsprojects.com/p/flask/) 3.1.1
- [Flask-SQLAlchemy](https://flask-sqlalchemy.palletsprojects.com/) 3.1.1
- SQLite (banco de dados)
- Jinja2 + HTML/CSS (templates e temas)
- [reveal.js](https://revealjs.com/) (apresentação em `slides.html`)

## Estrutura do projeto

```
task-manager/
├── app.py                    # Aplicação principal (rotas, modelos e API)
├── i18n.py                   # Traduções (Português/Inglês) e idioma padrão
├── tests.py                  # Testes automatizados (unittest)
├── slides.html               # Apresentação do projeto (reveal.js)
├── requirements.txt          # Dependências do projeto
├── .env.example              # Exemplo de variáveis de ambiente
├── README.md
├── static/
│   ├── style.css             # Estilos da interface (temas claro/escuro)
│   ├── logo-v2.svg           # Logomarca (vetorial)
│   ├── logo-v2.png           # Logomarca (bitmap)
│   ├── favicon.png           # Favicon 64x64
│   ├── logo-v2-favicon.png   # Favicon 32x32
│   └── apple-touch-icon.png  # Ícone para iOS
├── templates/
│   ├── base.html             # Layout base (sidebar, topbar, tema, i18n, flashes)
│   ├── home.html             # Página inicial (landing)
│   ├── tasks.html            # Listagem + filtros + paginação
│   ├── form.html             # Formulário de criação/edição (com tags e anexos)
│   └── reminders.html        # Envio de lembretes
├── uploads/                  # Arquivos anexados (gerado em tempo de execução)
└── instance/
    └── tasks.db              # Banco de dados SQLite (gerado automaticamente)
```

## Requisitos

- Python 3.8 ou superior
- `pip`

## Como executar

### 1. Entrar no diretório

```bash
cd task-manager
```

### 2. Criar e ativar o ambiente virtual (opcional, recomendado)

```bash
python3 -m venv venv
source venv/bin/activate       # Linux/macOS
# venv\Scripts\activate        # Windows
```

### 3. Instalar as dependências

```bash
pip install -r requirements.txt
```

### 4. Executar a aplicação

```bash
python app.py
```

O servidor inicia em `http://0.0.0.0:5000`. Acesse no navegador:

```
http://localhost:5000
```

> O banco de dados (`instance/tasks.db`) e a pasta `uploads/` são criados na primeira execução.

## Configuração (variáveis de ambiente)

Copie `.env.example` e ajuste conforme necessário:

| Variável              | Padrão                 | Descrição                                        |
|-----------------------|------------------------|--------------------------------------------------|
| `SECRET_KEY`          | aleatória por execução | Chave de sessão do Flask                         |
| `DATABASE_URL`        | `sqlite:///tasks.db`   | URI do banco de dados                            |
| `UPLOAD_FOLDER`       | `./uploads`            | Pasta de armazenamento dos anexos               |
| `MAX_CONTENT_LENGTH`  | `5242880` (5 MB)       | Tamanho máximo de upload, em bytes              |
| `MAIL_MODE`           | `console`              | `console` (não envia) ou `smtp`                 |
| `SMTP_HOST`           | `localhost`            | Servidor SMTP                                    |
| `SMTP_PORT`           | `25`                   | Porta SMTP                                       |
| `SMTP_USERNAME`       | —                      | Usuário SMTP (opcional)                         |
| `SMTP_PASSWORD`       | —                      | Senha SMTP (opcional)                           |
| `SMTP_USE_TLS`        | `0`                    | Ativa TLS (`1`/`0`)                              |
| `NOTIFY_EMAIL`        | `admin@localhost`      | Destinatário das notificações e lembretes       |

## Rotas e endpoints

### Interface web

| Método   | Rota                    | Descrição                                             |
|----------|-------------------------|-------------------------------------------------------|
| GET      | `/`                     | Página inicial (landing)                              |
| GET      | `/tasks`                | Lista tarefas (filtros, busca, ordenação e paginação) |
| GET      | `/create`               | Formulário de nova tarefa                             |
| POST     | `/create`               | Cria a tarefa (com tags e anexos)                     |
| GET      | `/edit/<id>`            | Formulário de edição                                  |
| POST     | `/edit/<id>`            | Atualiza a tarefa                                     |
| POST     | `/toggle/<id>`          | Alterna status pendente/concluída                     |
| POST     | `/delete/<id>`          | Exclui a tarefa (e seus anexos)                       |
| GET      | `/reminders`            | Página de envio de lembretes                          |
| POST     | `/reminders`            | Envia lembretes (campo `days`)                        |
| POST/GET | `/notify/overdue`       | Dispara notificação de tarefas atrasadas              |
| GET      | `/uploads/<filename>`   | Download de um anexo                                  |
| POST     | `/attachments/<id>/delete` | Remove um anexo                                    |
| GET      | `/favicon.ico`          | Favicon da aplicação                                  |

### Parâmetros de consulta em `GET /tasks`

| Parâmetro  | Valores                                                                 | Descrição                     |
|------------|-------------------------------------------------------------------------|-------------------------------|
| `status`   | `todas`, `pendentes`, `concluidas`, `atrasadas`, `hoje`                 | Filtro por status             |
| `priority` | `todas`, `alta`, `media`, `baixa`                                       | Filtro por prioridade         |
| `tag`      | nome da tag                                                             | Filtro por etiqueta           |
| `search`   | texto                                                                   | Busca em título/descrição     |
| `sort`     | `created_desc`, `created_asc`, `due_asc`, `due_desc`, `priority_desc`   | Ordenação                     |
| `page`     | inteiro                                                                 | Página da listagem (8 itens)  |
| `lang`     | `pt`, `en`                                                              | Idioma da interface           |

### API (JSON)

| Método | Rota                | Descrição                                          |
|--------|---------------------|----------------------------------------------------|
| GET    | `/api/tasks`        | Retorna todas as tarefas                           |
| POST   | `/api/tasks`        | Cria uma tarefa (201; 400 em dados inválidos)      |
| GET    | `/api/tasks/<id>`   | Retorna uma tarefa (404 se não existir)            |
| PUT    | `/api/tasks/<id>`   | Atualiza campos de uma tarefa                      |
| DELETE | `/api/tasks/<id>`   | Exclui a tarefa                                    |

Exemplo de resposta:

```json
{
  "tasks": [
    {
      "id": 1,
      "title": "Estudar Python",
      "description": "Capítulo 3",
      "priority": "media",
      "status": "pendente",
      "due_date": "2026-09-01",
      "created_at": "2026-08-28T10:00:00",
      "updated_at": "2026-08-28T10:00:00",
      "is_overdue": false,
      "is_due_today": false,
      "tags": ["estudo"],
      "attachments": [
        { "id": 1, "filename": "nota.txt", "url": "/uploads/abc123_nota.txt" }
      ]
    }
  ]
}
```

Exemplo de criação via API:

```bash
curl -X POST http://localhost:5000/api/tasks \
  -H "Content-Type: application/json" \
  -d '{"title": "Estudar Flask", "priority": "alta", "tags": ["estudo"]}'
```

## Modelo de dados

### `Task`

| Campo         | Tipo          | Obrigatório | Padrão      | Descrição                       |
|---------------|---------------|-------------|-------------|---------------------------------|
| `id`          | Integer (PK)  | Sim         | —           | Identificador único             |
| `title`       | String(200)   | Sim         | —           | Título da tarefa                |
| `description` | Text          | Não         | `""`        | Descrição detalhada             |
| `priority`    | String(10)    | Sim         | `media`     | `alta`, `media` ou `baixa`      |
| `status`      | String(10)    | Sim         | `pendente`  | `pendente` ou `concluida`       |
| `due_date`    | Date          | Não         | `NULL`      | Prazo limite                    |
| `created_at`  | DateTime      | Sim         | agora       | Data de criação                 |
| `updated_at`  | DateTime      | Sim         | agora       | Data da última atualização      |

**Propriedades calculadas**

- `is_overdue` — `True` se o prazo é anterior a hoje e a tarefa não está concluída.
- `is_due_today` — `True` se o prazo é hoje e a tarefa não está concluída.

### `Tag`

| Campo  | Tipo            | Descrição                          |
|--------|-----------------|------------------------------------|
| `id`   | Integer (PK)    | Identificador único                |
| `name` | String(60)      | Nome único da etiqueta             |

Relação **N:N** com `Task` (tabela associativa `task_tags`).

### `Attachment`

| Campo         | Tipo           | Descrição                                   |
|---------------|----------------|---------------------------------------------|
| `id`          | Integer (PK)   | Identificador único                         |
| `task_id`     | FK → `tasks`   | Tarefa associada                            |
| `filename`    | String(255)    | Nome original do arquivo                    |
| `stored_name` | String(255)    | Nome único no disco (prefixo UUID)          |
| `created_at`  | DateTime       | Data do upload                              |

Relação **N:1** com `Task` (remoção em cascata).

## Anexos

- Extensões permitidas: `pdf`, `png`, `jpg`, `jpeg`, `gif`, `txt`, `doc`, `docx`, `zip`.
- Tamanho máximo por requisição: **5 MB** (configurável via `MAX_CONTENT_LENGTH`).
- Arquivos são salvos em `uploads/` com um prefixo UUID e baixados por `/uploads/<stored_name>`.
- A remoção de um anexo (`/attachments/<id>/delete`) apaga também o arquivo do disco.

## Notificações e lembretes

- **Atrasadas** (`/notify/overdue`): envia a lista de tarefas com prazo vencido e não concluídas.
- **Lembretes** (`/reminders`): envia tarefas que vencem em até `days` dias **e** as atrasadas.
- Com `MAIL_MODE=console` (padrão), o conteúdo é impresso no terminal — útil para desenvolvimento.
- Com `MAIL_MODE=smtp`, o envio é feito via SMTP (com suporte opcional a TLS e autenticação).

## Internacionalização

- Idiomas: **Português (`pt`, padrão)** e **Inglês (`en`)**.
- As traduções ficam em `i18n.py` (dicionário `TRANSLATIONS`), sem dependências externas.
- Qualquer rota aceita `?lang=pt` ou `?lang=en`; a escolha é guardada na sessão.
- Datas são formatadas conforme o idioma (`DATE_FORMATS`).

## Tema, layout e acessibilidade

- **Tema claro/escuro** com alternância no topbar e preferência salva em `localStorage`.
- **Sidebar colapsável** com estado persistente.
- **Breadcrumbs** nas páginas internas e **mensagens flash** dispensáveis (auto-ocultam após 4s).
- **Skip link**, foco visível e atributos ARIA para navegação acessível.

## Apresentação (slides)

O arquivo `slides.html` contém uma apresentação do projeto usando reveal.js, com **alternância de tema claro/escuro** no canto superior direito.

Abra diretamente no navegador:

```bash
xdg-open slides.html    # Linux
# open slides.html      # macOS
```

## Testes

A suíte usa apenas a biblioteca padrão (`unittest`) e um banco SQLite temporário, isolado por teste.

```bash
python3 tests.py
# ou
python3 -m unittest
```

Cobertura atual (**13 testes**): render da home, criação/listagem, validação de título e data, edição, toggle de status, exclusão, filtro por status, paginação, troca de idioma e CRUD da API.

## Observações

- O `SECRET_KEY` é gerado aleatoriamente a cada execução (sessões são reiniciadas). Defina `SECRET_KEY` para sessões persistentes.
- A aplicação roda em modo `debug=True` por padrão ao executar `app.py`. Para produção, desative o modo debug e use um servidor WSGI (ex.: Gunicorn).
- O banco SQLite fica em `instance/tasks.db` e os anexos em `uploads/`.

## Melhorias futuras sugeridas

- [ ] Autenticação de usuários
- [ ] Testes para tags, anexos, lembretes e notificações
- [ ] Migrações de banco (ex.: Flask-Migrate)
- [ ] Agendador para envio automático de lembretes
