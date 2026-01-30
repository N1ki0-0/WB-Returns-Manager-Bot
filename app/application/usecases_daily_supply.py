from dataclasses import dataclass
from collections import defaultdict
from datetime import datetime
from zoneinfo import ZoneInfo
from collections import defaultdict
import asyncio
from app.domain.title_normalizer import normalize_phone_title
@dataclass
class DailySupplyResult:
    supply_id: str | None
    total_qty: int
    lines: list[str]

def _short_color_name(color: str) -> str:
    # Можно расширять, но базово — приводим к "бел.", "син.", "чер." и т.п.
    c = color.strip().lower()
    mapping = {
        "белый": "бел.",
        "белая": "бел.",
        "white": "бел.",
        "синий": "син.",
        "синяя": "син.",
        "blue": "син.",
        "черный": "чер.",
        "чёрный": "чер.",
        "black": "чер.",
        "фиолетовый": "фиол",
        "фиолетовая": "фиол",
        "purple": "фиол",
        "желтый": "жел.",
        "жёлтый": "жел.",
        "yellow": "жел.",
        "зеленый": "зел.",
        "зеленая": "зел.",
        "green": "зел.",
        "розовый": "роз.",
        "розовая": "роз.",
        "pink": "роз.",

    }
    return mapping.get(c, color)

class CreateDailySupplyUseCase:
    def __init__(
        self,
        marketplace_client,
        content_client,
        daily_repo,
        notifier,
        tz: str,
        enabled: bool,
        batch_size: int = 5, batch_pause_sec: int = 20, cards_limit: int = 100
    ):
        self._mp = marketplace_client
        self._content = content_client
        self._repo = daily_repo
        self._notifier = notifier
        self._tz = tz
        self._enabled = enabled
        self._cache: dict[int, tuple[str, str]] = {}  # nmId -> (title, color)
        self._batch_size = batch_size
        self._batch_pause_sec = batch_pause_sec

    async def run(self) -> DailySupplyResult:
        if not self._enabled:
            return DailySupplyResult(None, 0, ["DAILY_SUPPLY_ENABLED=false"])

        now = datetime.now(ZoneInfo(self._tz))
        day_key = now.strftime("%Y-%m-%d")

        if await self._repo.already_ran(day_key):
            return DailySupplyResult(None, 0, [f"Уже выполнялось сегодня ({day_key})."])

        try:
            resp = await self._mp.get_new_orders()
            orders = resp.get("orders", [])

            if not orders:
                text = f"WB Supply {day_key}: новых заказов нет."
                await self._repo.mark_ok(
                    day_key,
                    supply_id="",
                    created_at=now,
                    order_count=0,
                    report_text=text,
                )
                await self._notifier.notify_admins(text)
                return DailySupplyResult("", 0, ["Новых заказов нет."])

            order_ids = [int(o["id"]) for o in orders]
            # Один склад (как вы сказали). Если всё же появится другой — можно проверить warehouseId.

            supply_name = f"AutoSupply {day_key}"
            created = await self._mp.create_supply(supply_name)
            supply_id = created.get("id") or created.get("supplyId") or created.get("supplyID")
            if not supply_id:
                raise RuntimeError(f"Не удалось получить supply_id из ответа: {created}")

            await self._mp.add_orders_to_supply(supply_id, order_ids)

            nm_ids_needed = []
            for o in orders:
                nm_id = int(o["nmId"])
                if nm_id not in self._cache:
                    nm_ids_needed.append(nm_id)

            # 2) резолвим карточки пакетами: 5 запросов -> пауза 20 сек
            cards_errors = 0
            for i in range(0, len(nm_ids_needed), self._batch_size):
                batch = nm_ids_needed[i:i + self._batch_size]

                # делаем последовательно (предсказуемо по лимитам); можно параллельно, но вы просили “не штурмовать”
                for nm_id in batch:
                    try:
                        # fallback_color нам больше не нужен (цвет берем из title)
                        title, _color = await self._get_title_and_color(nm_id, fallback_color="")
                        self._cache[nm_id] = (title, "")  # цвет не используем
                    except Exception:
                        cards_errors += 1
                        self._cache[nm_id] = (f"UNKNOWN_{nm_id}", "")

                # пауза между пачками, если остались ещё
                if i + self._batch_size < len(nm_ids_needed):
                    await asyncio.sleep(self._batch_pause_sec)

            # 3) агрегация по нормализованному имени (а не nmId)
            agg: dict[str, int] = defaultdict(int)
            unknown_count = 0
            total = 0

            for o in orders:
                nm_id = int(o["nmId"])
                qty = int(o.get("quantity", 1))
                total += qty

                title = self._cache.get(nm_id, (f"UNKNOWN_{nm_id}", ""))[0]
                if title.startswith("UNKNOWN_"):
                    unknown_count += qty
                    continue

                key = normalize_phone_title(title)
                agg[key] += qty

            # 4) формируем лёгкочитаемый список
            lines = [f"{total} шт"]

            for name, qty in sorted(agg.items(), key=lambda x: (-x[1], x[0])):
                lines.append(f"{name} — {qty}")

            if unknown_count > 0:
                lines.append("")
                lines.append(f"Не распознано (карточка не получена): {unknown_count} шт.")

            if cards_errors > 0:
                lines.append(f"Примечание: были ошибки Content API при получении карточек: {cards_errors}.")

            text = f"WB Supply {day_key}\nСоздана поставка: {supply_id}\n\n" + "\n".join(lines)
            await self._notifier.notify_admins(text)

            await self._repo.mark_ok(
                day_key,
                supply_id=supply_id,
                created_at=now,
                order_count=len(order_ids),
                report_text=text,
            )

            return DailySupplyResult(supply_id, total, lines)

        except Exception as e:
            err = f"{type(e).__name__}: {e}"
            await self._repo.mark_failed(day_key, created_at=now, error=err)
            await self._notifier.notify_admins(f"WB Supply {day_key}: ошибка\n{err}")
            return DailySupplyResult(None, 0, [err])

    async def _get_title_and_color(self, nm_id: int, fallback_color: str) -> tuple[str, str]:
        if nm_id in self._cache:
            return self._cache[nm_id]

        # Поиск карточки через textSearch (nmId), берём первую подходящую
        data = await self._content.find_card_by_text(str(nm_id), locale="ru")
        cards = data.get("cards", []) or []

        title = f"nmId {nm_id}"
        color = fallback_color

        for c in cards:
            if int(c.get("nmID", 0)) != nm_id:
                continue
            title = c.get("title") or title

            # характеристика "Цвет"
            for ch in c.get("characteristics", []) or []:
                if (ch.get("name") or "").strip().lower() == "цвет":
                    vals = ch.get("value") or []
                    if isinstance(vals, list) and vals:
                        color = str(vals[0])
                    elif isinstance(vals, str):
                        color = vals
                    break
            break

        self._cache[nm_id] = (title, color)
        return title, color
