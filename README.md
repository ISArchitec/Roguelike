# Roguelike — «Бюро»

Пошаговая консольная игра о восстановлении документов. Проект разделён на модель игры, генерацию уровней, консольный интерфейс и сериализацию сохранений.

Запуск из корня проекта:

```bash
python -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python main.py
```

В Windows используйте `.venv\Scripts\python.exe`. Справка по управлению доступна командой `help` во время игры. Сохранения по умолчанию находятся в `saves/`; конфигурация — в `configs/config.json`.

Тесты:

```bash
.venv/bin/python -m pip install -r requirements-dev.txt
.venv/bin/python -m pytest tests
```

- [Описание системы и механик](docs/overall_description.md)
- [Требования](docs/requirements.md)
- [Конфигурация и сохранения](docs/configuration.md)
