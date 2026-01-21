# WB Returns Manager Bot

Telegram-бот для продавца Wildberries (FBS), который автоматизирует:
- обработку заявок на возврат по правилу “старше N дней”;
- ежедневное формирование одной поставки (supply) из всех новых заказов и отправку отчёта в Telegram;
- журналирование действий и ошибок (уведомления администраторам).

---

## 1) Быстрый старт (Docker)

### 1.1. Структура проекта
В корне проекта должны быть:
- `docker-compose.yml`
- `Dockerfile`
- `.env`
- папка `app/`
- папка `data/` (для SQLite)

### 1.2. Запуск
```bash
docker compose up -d --build
docker compose logs -f bot
