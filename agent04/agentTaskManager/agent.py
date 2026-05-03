from google.adk.agents.llm_agent import Agent
from trello import TrelloClient
from dotenv import load_dotenv
from datetime import datetime
import os
from zoneinfo import ZoneInfo

# Carrega as variáveis de ambiente do arquivo .env
load_dotenv()

# Credenciais do Trello lidas das variáveis de ambiente
API_KEY = os.getenv('TRELLO_API_KEY')
API_SECRET = os.getenv('TRELLO_API_SECRET')
TOKEN = os.getenv('TRELLO_TOKEN')

## Ferramenta para obter o contexto temporal (data e hora atual)
def get_temporal_context():
    """Retorna a data e a hora atual no fuso horário de São Paulo."""
    now = datetime.now(ZoneInfo("America/Sao_Paulo"))
    return now.strftime('%Y/%m/%d %H:%M:%S')
    card.set_due(now)

## Ferramenta para adicionar uma nova tarefa no Trello 
def adicionar_tarefa(nome_da_task:str,descricao_da_task:str,due_date:str):
    client = TrelloClient(
        api_key = API_KEY,
        api_secret = API_SECRET,
        token = TOKEN
    )

    # Busca os boards disponíveis e seleciona o board chamado 'DIO'
    boards = client.list_boards()
    my_board = [b for b in boards if b.name == 'DIO'][0]

    # Localiza a lista de tarefas pendentes na board
    listas = my_board.list_lists()
    my_list = [l for l in listas if l.name.upper() == 'TO DO' or l.name.upper() == 'A FAZER'][0]

    # Cria um novo card com título, descrição e data de vencimento
    my_list.add_card(
        name = nome_da_task,
        desc = descricao_da_task,
        due = due_date
    )

## Ferramenta para listar as tarefas do Trello, com opção de filtrar por status
def listar_tarefas(status:str="todas"):
    client = TrelloClient(
        api_key = API_KEY,
        api_secret = API_SECRET,
        token = TOKEN
    )

    client.list_boards()
    boards = client.list_boards()
    my_board = [b for b in boards if b.name == 'DIO'][0]
    listas = my_board.list_lists()
    
    # Filtra as listas do Trello pelo status solicitado
    if status.lower() == "todas":
        listas_filtradas = listas
    elif status.lower() == "a fazer":
        listas_filtradas = [l for l in listas if l.name.upper() in ['TO DO','A FAZER','TODO']]
    elif status.lower() == "em andamento":
        listas_filtradas = [l for l in listas if l.name.upper() in ['DOING','EM ANDAMENTO']]
    elif status.lower() == "concluído":
        listas_filtradas = [l for l in listas if l.name.upper() in ['DONE','CONCLUÍDO','CONCLUIDO']]
    else:
        listas_filtradas = listas

    tarefas = []

    # Constrói uma lista de dicionários contendo os dados de cada card
    for lista in listas_filtradas:
        cards = lista.list_cards()
        for card in cards:
            tarefas.append({
                "nome": card.name,
                "descrição": card.desc,
                "vencimento": card.due,
                "status": lista.name,
                "id": card.id
            })
              

    
    return tarefas

## Ferramenta para mudar o status de uma tarefa, movendo o card para a lista correspondente no Trello
def mudar_status(nome_da_task:str,novo_status:str)->str:
    try:   
        client = TrelloClient(
            api_key = API_KEY,
            api_secret = API_SECRET,
            token = TOKEN
        )

        client.list_boards()
        boards = client.list_boards()
        my_board = [b for b in boards if b.name == 'DIO'][0]

        listas = my_board.list_lists()

        # Mapeia nomes de status para os nomes usados nas listas do Trello
        status_map = {
            "a fazer": "A FAZER",
            "em andamento": "EM ANDAMENTO",
            "concluído": "CONCLUÍDO"
        }

        nome_lista_destino = status_map.get(novo_status.lower())

        if not nome_lista_destino:
            return f"ERRO: Status Inválido. Use 'a fazer', 'em andamento' ou 'concluído'."

        lista_destino = next(
            (l for l in listas if l.name.upper() == nome_lista_destino.upper()),
            None
        )

        if not lista_destino:
            return f"ERRO: Lista '{nome_lista_destino}' não encontrada no board."
    
        card_encontrado = None
        lista_origem = None

        # Procura o card pelo nome em todas as listas
        for lista in listas:
            cards = lista.list_cards()
            card_encontrado = next(
                (c for c in cards if c.name.lower() == nome_da_task.lower()),
                None
            )
            if card_encontrado:
                lista_origem = lista
                break
        if not card_encontrado:
            return f"ERRO: Card '{nome_da_task}' não encontrado"
    
        # Move o card para a lista de destino
        card_encontrado.change_list(lista_destino.id)
        return f"'{nome_da_task}': {lista_origem} -> {lista_destino}"
    except Exception as e:
        return f"ERRO: {str(e)}"

# Agente que expõe as ferramentas para o LLM
root_agent = Agent(
    model='gemini-2.5-flash',
    name='root_agent',
    description='Você é um agente de organização de tarefas.',
    instruction="""
        Você é um agente de organização de tarefas.
        Sua função é receber uma tarefa e criar um card no Trello com o nome e a descrição da tarefa.
        Você deve perguntar as atividades que tenho no dia e criar um card para cada uma delas.
        Você inicia a conversa assim que for ativado perguntando quais são as tarefas do dia.
        Sempre inicia a conversa perguntando as tarefas do dia e informando a data pela tool get-temporal-context, e depois vá perguntando se tem mais tarefas até que o usuário responda que não.
        Suas funções:
        1. Adicionar novas tarefas com nome e descrição.
        2. Listar todas as tarefas ou filtrar por status.
        3. Marcar tarefas como concluídas.
        4. Remover tarefa da lista.
        5. Mudar o status da tarefa (exemplo: de 'A Fazer' para 'Em Andamento' e de 'Em Andamento' para 'Concluído').
        6. Gerar contexto temporal (data e hora atual) para organizar as tarefas do dia.
""",
    tools = [get_temporal_context,adicionar_tarefa,listar_tarefas,mudar_status]
)