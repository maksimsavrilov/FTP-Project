import os
import sys
import json
import time
import subprocess
import typing_extensions as typing
from typing import Literal
from pydantic import BaseModel, Field
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.sqlite import SqliteSaver

# =====================================================================
# 1. СТРУКТУРА ДАННЫХ И STATE
# =====================================================================

class FileTask(BaseModel):
    file_path: str = Field(description="Относительный путь к файлу (например, 'app/models/user.py')")
    action: str = Field(description="Действие: 'create' (создать новый) или 'modify' (изменить)")
    description: str = Field(description="Подробная техническая задача для реализации")

class Blueprint(BaseModel):
    tasks: list[FileTask] = Field(description="Список последовательных задач по файлам")
    explanation: str = Field(description="Обоснование плана")

class ProjectState(typing.TypedDict):
    c4_dsl: str
    domain_model: str
    requirements: str
    project_structure: str   
    
    target_tasks: list[dict] 
    current_task_index: int  
    
    coder_feedback: str      
    iterations_per_file: int 

# Настройка задержки (60 секунд для лимитов OpenAI Free, либо 3600 для паузы в 1 час)
DELAY_SECONDS = 3600

llm = ChatOpenAI(model="gpt-5.6-luna", temperature=0.1)
structured_planner = llm.with_structured_output(Blueprint)

# =====================================================================
# 2. ИНСТРУМЕНТЫ ФАЙЛОВОЙ СИСТЕМЫ (Tools)
# =====================================================================

@tool
def read_project_file(file_path: str) -> str:
    """Читает содержимое файла проекта. Используйте перед модификацией кода."""
    if not os.path.exists(file_path):
        return f"Файл {file_path} еще не существует."
    with open(file_path, "r", encoding="utf-8") as f:
        return f.read()

@tool
def write_project_file(file_path: str, content: str) -> str:
    """Записывает или полностью перезаписывает код в файл проекта на диск."""
    os.makedirs(os.path.dirname(file_path) or '.', exist_ok=True)
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(content)
    return f"Файл {file_path} успешно сохранен на диск."

llm_with_tools = llm.bind_tools([read_project_file, write_project_file])

# =====================================================================
# 3. УЗЛЫ ВОРКФЛОУ (Nodes)
# =====================================================================

def planner_node(state: ProjectState) -> dict:
    """Шаг 1: Анализирует архитектуру и составляет бэклог задач."""
    # Если мы восстановились из бэкапа и план уже есть, не перегенерируем его
    if state.get("target_tasks"):
        print("\n🧠 [ПЛАНИРОВЩИК] План уже существует в базе данных. Пропускаю генерацию.")
        return {}

    print("\n🧠 [УЗЕЛ: ПЛАНИРОВЩИК] Сопоставляю C4/MD-требования с текущими файлами...")
    
    system_prompt = (
        "Ты — Главный Архитектор системы. Сравни целевую архитектуру (C4, доменную модель, требования) "
        "с текущей структурой проекта. Сформируй пошаговый список задач по созданию или изменению файлов Python."
    )
    user_prompt = f"""
    === C4 DSL ===\n{state['c4_dsl']}
    === ДОМЕННАЯ МОДЕЛЬ ===\n{state['domain_model']}
    === ТРЕБОВАНИЯ ===\n{state['requirements']}
    === ТЕКУЩИЕ ФАЙЛЫ В ПАПКЕ ===\n{state['project_structure']}
    """
    
    result: Blueprint = structured_planner.invoke([SystemMessage(content=system_prompt), HumanMessage(content=user_prompt)])
    tasks_dict = [task.model_dump() for task in result.tasks]
    
    print(f"📋 Планировщик создал список из {len(tasks_dict)} задач. Сохраняю в БД.")
    print(f"⏳ Ожидание {DELAY_SECONDS} сек. перед передачей задачи кодеру...")
    time.sleep(DELAY_SECONDS)
    
    return {"target_tasks": tasks_dict, "current_task_index": 0}


def coder_node(state: ProjectState) -> dict:
    """Шаг 2: Берет одну текущую задачу и пишет/изменяет файл."""
    idx = state["current_task_index"]
    tasks = state["target_tasks"]
    
    if idx >= len(tasks):
        return {}
        
    current_task = tasks[idx]
    print(f"\n🛠️ [УЗЕЛ: КОДЕР] Задача {idx + 1}/{len(tasks)}: Работаю над файлом {current_task['file_path']}...")
    
    system_prompt = (
        "Ты — Старший разработчик. Твоя задача — реализовать или изменить один конкретный файл.\n"
        "Обязательно используй инструмент write_project_file, чтобы зафиксировать изменения на диске!\n"
        "Если тебе прислали логи ошибок от pytest — исправь их."
    )
    user_prompt = f"""
    Файл: {current_task['file_path']}
    Действие: {current_task['action']}
    Что нужно сделать: {current_task['description']}
    === ОШИБКИ ИЗ ТЕРМИНАЛА (ОТ ТЕСТОВ) ===\n{state.get('coder_feedback', 'Ошибок нет.')}
    """
    
    response = llm_with_tools.invoke([SystemMessage(content=system_prompt), HumanMessage(content=user_prompt)])
    
    if response.tool_calls:
        for tool_call in response.tool_calls:
            if tool_call["name"] == "read_project_file":
                content = read_project_file.invoke(tool_call["args"])
                time.sleep(2) 
                follow_up = llm_with_tools.invoke([SystemMessage(content=system_prompt), HumanMessage(content=user_prompt), HumanMessage(content=f"Контент файла:\n{content}")])
                if follow_up.tool_calls:
                    for fc in follow_up.tool_calls:
                        if fc["name"] == "write_project_file":
                            write_project_file.invoke(fc["args"])
            elif tool_call["name"] == "write_project_file":
                write_project_file.invoke(tool_call["args"])
                
    print(f"⏳ Файл изменен. Ожидание {DELAY_SECONDS} сек. перед запуском тестов...")
    time.sleep(DELAY_SECONDS)
                
    return {"iterations_per_file": state.get("iterations_per_file", 0) + 1}


def tester_node(state: ProjectState) -> dict:
    """Шаг 3: Запускает pytest в терминале."""
    print("🧪 [УЗЕЛ: ТЕСТИРОВЩИК] Запускаю pytest...")
    result = subprocess.run(["pytest"], capture_output=True, text=True)
    
    if result.returncode == 0:
        print("✅ Тесты прошли успешно!")
        return {"coder_feedback": ""} 
    else:
        print("❌ Тесты упали. Логи сохранены в State для исправления.")
        return {"coder_feedback": result.stdout + "\n" + result.stderr}

# =====================================================================
# 4. ЛОГИКА ПЕРЕХОДОВ И ВСПОМОГАТЕЛЬНЫЕ УЗЛЫ
# =====================================================================

def test_and_progress_router(state: ProjectState) -> Literal["coder", "check_next_task"]:
    if state.get("coder_feedback") and state.get("iterations_per_file", 0) < 3:
        print("🔁 Возвращаем кодеру на исправление ошибок.")
        return "coder"
    return "check_next_task"

def check_next_task_node(state: ProjectState) -> dict:
    return {
        "current_task_index": state["current_task_index"] + 1,
        "iterations_per_file": 0,
        "coder_feedback": ""
    }

def tasks_exhausted_router(state: ProjectState) -> Literal["coder", "__end__"]:
    if state["current_task_index"] < len(state["target_tasks"]):
        return "coder"
    return END

# =====================================================================
# 5. СБОРКА ГРАФА И ИНИЦИАЛИЗАЦИЯ SQLITE PERSISTENCE
# =====================================================================

def scan_folder(root_dir=".") -> str:
    ignored = {'.git', '__pycache__', '.pytest_cache', 'venv', '.venv'}
    files_list = []
    for root, dirs, files in os.walk(root_dir):
        dirs[:] = [d for d in dirs if d not in ignored]
        for f in files:
            if f.endswith('.py') or f.endswith('.md') and f != "ai_developer.py":
                files_list.append(os.path.relpath(os.path.join(root, f), root_dir))
    return "\n".join(files_list)

def load_file_content_if_exists(filenames: list[str], default_text: str = "") -> str:
    for filename in filenames:
        if os.path.exists(filename):
            print(f"📖 [Загрузка] Читаю файл архитектуры: {filename}")
            with open(filename, "r", encoding="utf-8") as f:
                return f.read()
    return default_text

# Инициализируем хранилище SQLite
memory = SqliteSaver.from_conn_string("state_history.db")

workflow = StateGraph(ProjectState)
workflow.add_node("planner", planner_node)
workflow.add_node("coder", coder_node)
workflow.add_node("tester", tester_node)
workflow.add_node("check_next_task", check_next_task_node)

workflow.add_edge(START, "planner")
workflow.add_edge("planner", "coder")
workflow.add_edge("coder", "tester")
workflow.add_conditional_edges("tester", test_and_progress_router)

workflow.add_edge("check_next_task", "gateway")
workflow.add_node("gateway", lambda x: x)
workflow.add_conditional_edges("gateway", tasks_exhausted_router)

# Компилируем граф, передавая объект памяти checkpointer
app = workflow.compile(checkpointer=memory)

# =====================================================================
# 6. ЗАПУСК
# =====================================================================

if __name__ == "__main__":
    if not os.environ.get("OPENAI_API_KEY"):
        print("❌ Ошибка: Укажите ваш API-ключ в переменной окружения.")
        sys.exit(1)

    # Идентификатор сессии (thread_id). По нему LangGraph понимает, какую историю загрузить.
    # Если вы хотите начать абсолютно новый проект, просто измените "project_v1" на другое имя.
    config = {"configurable": {"thread_id": "project_v1"}}

    # Проверяем, есть ли уже сохраненная история для этой сессии
    existing_state = app.get_state(config)
    
    if existing_state.values:
        print("\n💾 [БЭКАП] Найдена сохраненная сессия! Восстанавливаю состояние...")
        print(f"Остановились на задаче индекс: {existing_state.values.get('current_task_index', 0)}")
        initial_input = None  # Не передаем входные данные, граф подтянет старые сам
    else:
        print("\n🆕 Создаю новую сессию разработки...")
        c4_context = load_file_content_if_exists(["c4.dsl", "C4.dsl", "architecture.dsl"], "# Нет схемы")
        domain_context = load_file_content_if_exists(["domain.md", "DOMAIN.md", "domain_model.md"], "# Нет домена")
        requirements_context = load_file_content_if_exists(["requirements.md", "REQUIREMENTS.md"], "# Нет требований")
        current_structure = scan_folder()
        initial_input = {
            "c4_dsl": c4_context,
            "domain_model": domain_context,
            "requirements": requirements_context,
            "project_structure": current_structure if current_structure else "Папка пуста",
            "target_tasks": [],
            "current_task_index": 0,
            "coder_feedback": "",
            "iterations_per_file": 0
        }
    print("🚀 Запуск конвейера...")
    # Передаем конфигурацию с thread_id
    final_state = app.invoke(initial_input, config=config)
    print("\n==================================================")
    print("🎉 Все доступные задачи из бэклога успешно выполнены!")