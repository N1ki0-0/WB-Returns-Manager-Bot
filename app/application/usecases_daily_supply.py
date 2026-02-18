from dataclasses import dataclass
from collections import defaultdict
import logging
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
        product_cache_repo=None,   # ← СТАЛ НЕОБЯЗАТЕЛЬНЫМ
        batch_size: int = 10,
        batch_pause_sec: int = 8,
        cards_limit: int = 150,
        instance_name: str = "default"
    ):
        self._mp = marketplace_client
        self._content = content_client
        self._repo = daily_repo
        self._notifier = notifier
        self._tz = tz
        self._enabled = enabled
        self._cache: dict[int, tuple[str, str]] = {}
        self._product_cache_repo = product_cache_repo  # может быть None
        self._content_sem = asyncio.Semaphore(3)
        self._batch_size = batch_size
        self._batch_pause_sec = batch_pause_sec
        self._cards_limit = cards_limit
        self._instance_name = instance_name
        self._log = logging.getLogger(f"daily_supply.{self._instance_name}")

    async def run(self) -> DailySupplyResult:
        """
        Надёжный запуск: всегда возвращаем DailySupplyResult.
        Логика:
         - получаем новые заказы
         - создаём поставку
         - пытаемся резолвить карточки пакетами, с fallback'ом на поля заказа
         - формируем читаемый список и уведомляем админов
        """
        if not self._enabled:
            return DailySupplyResult(None, 0, ["DAILY_SUPPLY_ENABLED=false"])

        now = datetime.now(ZoneInfo(self._tz))
        day_key = now.strftime("%Y-%m-%d")

        # Safety: any interaction with repo/clients should not raise unhandled exceptions
        try:
            already = False
            try:
                already = await self._repo.already_ran(day_key)
            except Exception as e:
                # repo may be flaky in tests — just log and continue
                self._log and self._log.warning("already_ran check failed: %s", e)
                already = False

            if already:
                return DailySupplyResult(None, 0, [f"Уже выполнялось сегодня ({day_key})."])

            # 1) get new orders
            resp = await self._mp.get_new_orders()
            orders = resp.get("orders", []) if isinstance(resp, dict) else []

            if not orders:
                text = f"WB Supply {day_key}: новых заказов нет."
                try:
                    await self._repo.mark_ok(day_key, supply_id="", created_at=now, order_count=0, report_text=text)
                except Exception:
                    self._log and self._log.debug("mark_ok failed for empty orders")
                try:
                    await self._notifier.notify_admins(text)
                except Exception:
                    self._log and self._log.debug("notify_admins failed for empty orders")
                return DailySupplyResult("", 0, ["Новых заказов нет."])

            # 2) create supply
            order_ids = [int(o["id"]) for o in orders]
            supply_name = f"{self._instance_name} AutoSupply {day_key}"

            created = await self._mp.create_supply(supply_name)
            supply_id = created.get("id") or created.get("supplyId") or created.get("supplyID")
            if not supply_id:
                raise RuntimeError(f"Не удалось получить supply_id из ответа: {created}")

            await self._mp.add_orders_to_supply(supply_id, order_ids)

            # 3) prepare fallback names per nmId from orders
            nm_ids_needed = []
            order_fallback_by_nm: dict[int, str] = {}
            for o in orders:
                nm_id = int(o["nmId"])
                fb = (o.get("offerName") or o.get("subjectName") or o.get("vendorCode") or "").strip()
                order_fallback_by_nm.setdefault(nm_id, fb)
                if nm_id not in self._cache:
                    nm_ids_needed.append(nm_id)

            # 4) batch resolve via Content API with pauses; store into self._cache
            cards_errors = 0

            async def resolve_one(nm_id: int):
                fallback_name = order_fallback_by_nm.get(nm_id, "")
                try:
                    title, color = await self._get_title_and_color(nm_id, fallback_name)
                    if not title:
                        title = fallback_name or f"nmId {nm_id}"
                    self._cache[nm_id] = (title, color or "")
                except Exception as ex:
                    self._log.debug("resolve nmId %s failed: %s", nm_id, ex)
                    fb = fallback_name or f"nmId {nm_id}"
                    self._cache[nm_id] = (fb, "")

            tasks = []
            for nm_id in nm_ids_needed:
                tasks.append(resolve_one(nm_id))

            # выполняем параллельно, но semaphore внутри ограничит нагрузку
            await asyncio.gather(*tasks)

            # 5) aggregate by normalized short name
            agg: dict[str, int] = defaultdict(int)
            total = 0
            for o in orders:
                nm_id = int(o["nmId"])
                qty = int(o.get("quantity", 1))
                total += qty

                title, color = self._cache.get(
                    nm_id,
                    (o.get("offerName") or o.get("subjectName") or f"nmId {nm_id}", "")
                )

                full_title = f"{title} {_short_color_name(color)}".strip()
                key = normalize_phone_title(full_title)
                agg[key] += qty

            # 6) if nothing matched (very unlikely), fallback to short names from orders
            lines: list[str]
            if not agg:
                fallback_map: dict[str, int] = {}
                for o in orders:
                    name = (o.get("offerName") or o.get("subjectName") or o.get(
                        "vendorCode") or f"nmId {o.get('nmId')}")
                    short = " ".join(str(name).split()[:2])
                    fallback_map[short] = fallback_map.get(short, 0) + int(o.get("quantity", 1))
                lines = [f"{sum(fallback_map.values())} шт"]
                for k, v in sorted(fallback_map.items(), key=lambda x: (-x[1], x[0])):
                    lines.append(f"{k} — {v}")
                text = f"WB Supply {day_key}\nСоздана поставка: {supply_id}\n\n" + "\n".join(lines)
                try:
                    await self._notifier.notify_admins(text)
                except Exception:
                    self._log and self._log.debug("notify_admins failed for fallback list")
                try:
                    await self._repo.mark_ok(day_key, supply_id=supply_id, created_at=now, order_count=len(order_ids),
                                             report_text=text)
                except Exception:
                    self._log and self._log.debug("mark_ok failed for fallback list")
                return DailySupplyResult(supply_id, total, lines)

            # 7) build final readable lines
            lines = [f"{total} шт"]
            for name, qty in sorted(agg.items(), key=lambda x: (-x[1], x[0])):
                lines.append(f"{name} — {qty}")

            if cards_errors > 0:
                lines.append("")
                lines.append(
                    f"Примечание: были ошибки Content API при получении карточек: {cards_errors}. (часть имён взяты из полей заказов)")

            text = f"WB Supply {day_key}\nСоздана поставка: {supply_id}\n\n" + "\n".join(lines)

            # 8) notify and persist (best-effort, do not raise)
            try:
                await self._notifier.notify_admins(text)
            except Exception:
                self._log and self._log.exception("notify_admins failed")

            try:
                await self._repo.mark_ok(day_key, supply_id=supply_id, created_at=now, order_count=len(order_ids),
                                         report_text=text)
            except Exception:
                self._log and self._log.exception("mark_ok failed")

            # debug print (visible in tests with -s)
            self._log and self._log.debug("Daily supply report:\n%s", text)

            return DailySupplyResult(supply_id, total, lines)

        except Exception as e:
            # final safety: do not re-raise; attempt minimal reporting and return result object
            err = f"{type(e).__name__}: {e}"
            self._log and self._log.exception("Unhandled exception in CreateDailySupplyUseCase.run: %s", e)

            # try to persist failure without raising
            try:
                if hasattr(self._repo, "mark_failed"):
                    await self._repo.mark_failed(day_key, created_at=now, error=err)
            except Exception:
                self._log and self._log.debug("mark_failed failed")

            try:
                await self._notifier.notify_admins(f"❌ WB Supply {day_key}: ошибка\n{err}")
            except Exception:
                self._log and self._log.debug("notify_admins failed in exception handler")

            return DailySupplyResult(None, 0, [err])

    async def _get_title_and_color(self, nm_id: int, fallback_name: str = "") -> tuple[str, str]:
        """
        Устойчивый резолв карточки:
        1) persistent cache
        2) Content API (с semaphore + retry 429)
        3) fallback из заказа
        4) nmId
        """

        # ---------- 1. ПЕРСИСТЕНТНЫЙ КЭШ ----------
        try:
            if self._product_cache_repo:
                cached = await self._product_cache_repo.get(nm_id)
                if cached and cached.title:
                    return cached.title, (cached.color or "")
        except Exception as e:
            self._log.debug("Cache read error nmId %s: %s", nm_id, e)

        # ---------- 2. CONTENT API С ОГРАНИЧЕНИЕМ И RETRY ----------
        for attempt in range(5):  # до 5 попыток
            try:
                async with self._content_sem:  # ограничиваем параллелизм
                    data = await self._content.find_card_by_text(str(nm_id), locale="ru")

                cards = data.get("cards") or []
                for c in cards:
                    try:
                        if int(c.get("nmID", 0)) != nm_id:
                            continue
                    except Exception:
                        continue

                    title = c.get("title")
                    color = ""
                    for ch in c.get("characteristics") or []:
                        if (ch.get("name") or "").strip().lower() == "цвет":
                            val = ch.get("value")
                            if isinstance(val, list) and val:
                                color = str(val[0])
                            elif isinstance(val, str):
                                color = val
                            break

                    if title:
                        try:
                            if self._product_cache_repo:
                                await self._product_cache_repo.set(nm_id, title, color)
                        except Exception:
                            self._log.debug("Cache write fail nmId %s", nm_id)

                        return title, color

                # карточки пришли, но нужной нет — дальше retry не нужен
                break

            except Exception as e:
                msg = str(e).lower()

                if "429" in msg or "too many requests" in msg:
                    wait = 2 ** attempt  # экспоненциальный backoff: 1,2,4,8,16
                    self._log.warning("429 Content API nmId %s → retry in %ss", nm_id, wait)
                    await asyncio.sleep(wait)
                    continue

                self._log.debug("Content API error nmId %s: %s", nm_id, e)
                break

        # ---------- 3. FALLBACK ИЗ ЗАКАЗА ----------
        if fallback_name:
            try:
                if self._product_cache_repo:
                    await self._product_cache_repo.set(nm_id, fallback_name, "")
            except Exception:
                pass
            return fallback_name, ""

        # ---------- 4. ПОСЛЕДНИЙ FALLBACK ----------
        fallback = f"nmId {nm_id}"
        try:
            if self._product_cache_repo:
                await self._product_cache_repo.set(nm_id, fallback, "")
        except Exception:
            pass

        return fallback, ""
