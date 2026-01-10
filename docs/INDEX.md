# Documentation Index

Навигация по документации проекта REGGY.

## Ключевые документы

| Документ | Описание |
|----------|----------|
| [../CLAUDE.md](../CLAUDE.md) | **Обязательный workflow** для Claude Code |
| [TARGET_WORKFLOW.md](TARGET_WORKFLOW.md) | Архитектура 8-этапного workflow |
| [ARCHITECTURE.md](ARCHITECTURE.md) | Системная архитектура проекта |
| [IMPLEMENTATION_PLAN.md](IMPLEMENTATION_PLAN.md) | План миграции на TARGET_WORKFLOW |
| [REFACTORING.md](REFACTORING.md) | Roadmap рефакторинга кода |

## Guides (Руководства)

| Документ | Описание |
|----------|----------|
| [guides/QUICKSTART.md](guides/QUICKSTART.md) | Быстрый старт: установка и запуск |
| [guides/SETUP_AIMLAPI.md](guides/SETUP_AIMLAPI.md) | Настройка API ключей PiAPI |
| [guides/TROUBLESHOOTING.md](guides/TROUBLESHOOTING.md) | Решение типичных проблем |

## Analysis (Анализ)

| Документ | Описание |
|----------|----------|
| [analysis/WORKFLOW_ANALYSIS.md](analysis/WORKFLOW_ANALYSIS.md) | Анализ pipeline, найденные проблемы |
| [analysis/ARCHITECTURE_REVIEW.md](analysis/ARCHITECTURE_REVIEW.md) | Обзор архитектуры, оценка 5/10 |
| [analysis/AUDIT_REPORT_2026_01_10.md](analysis/AUDIT_REPORT_2026_01_10.md) | Аудит документации vs код |
| [analysis/prompt-hypotheses.md](analysis/prompt-hypotheses.md) | Исследование промпт-инжиниринга |

## Planning (Планирование)

| Документ | Описание |
|----------|----------|
| [planning/PLAN_BREAKPOINTS_SYSTEM.md](planning/PLAN_BREAKPOINTS_SYSTEM.md) | План фикса workflow_mode |
| [planning/TODO_refactoring.md](planning/TODO_refactoring.md) | TODO по рефакторингу |
| [planning/TODO_step_versioning.md](planning/TODO_step_versioning.md) | TODO по версионированию шагов |

## Sessions (Сессии разработки)

| Документ | Описание |
|----------|----------|
| [sessions/session-2026-01-07-001.md](sessions/session-2026-01-07-001.md) | Сессия 07.01: архитектурные решения |
| [sessions/session-2026-01-09.md](sessions/session-2026-01-09.md) | Сессия 09.01: краткие заметки |
| [sessions/SESSION_2026_01_10_WORKFLOW_DOC.md](sessions/SESSION_2026_01_10_WORKFLOW_DOC.md) | Сессия 10.01: обновление workflow |

## Specs & RCA

| Папка | Описание |
|-------|----------|
| [specs/](specs/) | Технические спецификации (SPEC-*.md) |
| [rca/](rca/) | Root Cause Analysis для багов (RCA-*.md) |

---

## Структура документации

```
docs/
├── INDEX.md                    # Этот файл
├── TARGET_WORKFLOW.md          # Канонический spec workflow
├── ARCHITECTURE.md             # Архитектура системы
├── IMPLEMENTATION_PLAN.md      # План миграции
├── REFACTORING.md              # Roadmap рефакторинга
├── guides/                     # Руководства по установке
├── analysis/                   # Аналитические отчёты
├── planning/                   # Планы и TODO
├── sessions/                   # Логи сессий разработки
├── specs/                      # Технические спецификации
└── rca/                        # Root Cause Analysis
```

---

*Обновлено: 2026-01-10*
