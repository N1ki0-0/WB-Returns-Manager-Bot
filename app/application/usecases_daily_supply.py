from dataclasses import dataclass
from collections import defaultdict
from datetime import datetime
from zoneinfo import ZoneInfo

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
    ):
        self._mp = marketplace_client
        self._content = content_client
        self._repo = daily_repo
        self._notifier = notifier
        self._tz = tz
        self._enabled = enabled
        self._cache: dict[int, tuple[str, str]] = {}  # nmId -> (title, color)

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

            # Агрегация: nmId -> qty (обычно qty=1 на заказ, но оставим расширяемо)
            agg: dict[tuple[str, str], int] = defaultdict(int)
            total = 0

            # 1) Подготовим справочник nmId -> (title, color) одним проходом по уникальным nmId
            unique_nmids = sorted({int(o["nmId"]) for o in orders})
            cards_errors = 0
            resolved: dict[int, tuple[str, str]] = {}

            for nm_id in unique_nmids:
                # fallback если карточки не получим
                resolved[nm_id] = (f"nmId {nm_id}", "")

                try:
                    title, color = await self._get_title_and_color(nm_id, fallback_color="")
                    resolved[nm_id] = (title, color)
                except Exception:
                    cards_errors += 1
                    # оставляем fallback; НЕ валим весь job

            # 2) Агрегируем заказы, используя resolved + fallback на colorCode
            for o in orders:
                nm_id = int(o["nmId"])
                qty = int(o.get("quantity", 1))
                total += qty

                title, color = resolved.get(nm_id, (f"nmId {nm_id}", ""))

                # если цвет не удалось получить из карточки — пробуем взять из заказа
                if not color:
                    color = str(o.get("colorCode", "")).strip()

                color_short = _short_color_name(color) if color else ""
                key = (title, color_short)
                agg[key] += qty
            lines = []
            lines.append(f"{total} шт")
            for (title, color_short), qty in sorted(agg.items(), key=lambda x: (-x[1], x[0][0], x[0][1])):
                suffix = f" {color_short}" if color_short else ""
                lines.append(f"{title}{suffix} - {qty} шт.")

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
