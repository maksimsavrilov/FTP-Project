This file describes architecture of simple independent agentic coding program, implemented using graph based state/context internal model.

The implementation language is Python/LangGraph

Agents are:

    - Architect: System architect/analyst, keeps all the architecture of the project, develops requirements:
        - user
        - functional
        - non-functional
        review changes, split tasks into small pieces for developing and feed the developing queue, tracks the progress and compliances
    - Developer: Mid-level Python developer, processing development tasks
    - Tester: QA specialist, checking the code is covered by tests, tests are correct, and tests runs are green.

```text
              ┌────────────────┐
              │ Initialization │
              │ build state    │
              └───────┬────────┘
                      ↓
              ┌──────────────┐
              │  Architect   │
              └───────┬──────┘
                      ↓
              ┌──────────────┐
              │   Developer  │
              └───────┬──────┘
                      ↓
              ┌──────────────┐
              │    Tester    │
              └───────┬──────┘
                      ↓
                 tests OK?
                 /       \
               no         yes
               ↓           ↓
          Developer    Architect
                           │
                    iteration count
                           │
                    ┌──────┴──────┐
                    │             │
                  normal       periodic
                    │             │
                    ↓             ↓
                Developer    Architecture
                              audit + roadmap
                                   │
                                   ↓
                              Architect
```

The very initial state is built of following files:

    - /home/maksim/FTP Project/README.md
    - /home/maksim/FTP Project/AGENTS.md
    - /home/maksim/FTP Project/STATE.md
    - /home/maksim/FTP Project/structurizr/workspace.dsl
    - /home/maksim/FTP Project/roadmap.md
    - /home/maksim/FTP Project/docs/temp_db.sql

The LLM is gpt-5.6-luna on high reasoning for architect and medium-low for coding and testing

there are some graph development implementations like
    
    1. https://github.com/langchain-ai/open-swe
    2. https://github.com/DataRohit/Nexus
    3. https://github.com/CodeHub5199/Autonomous-Coder-Agent

the complete arch would be implemented like

```text
                FTP-Project
                    │
                 STATE.md
                 AGENTS.md
                 roadmap.md
                 architecture
                       │
                       ↓
                  Open SWE /
                 Deep Agents
                       │
              ┌────────┴────────┐
              ↓                 ↓
          Architect          Developer
              │                 │
              └────────┬────────┘
                       ↓
                    Tester
                       │
                 tests failed?
                  /          \
                yes           no
                 │             │
              Developer     Loop limit reached
                                /          \
                            yes            no
                             │              │
                         Architect       Developer            
                                            
                            
                            
                            
```