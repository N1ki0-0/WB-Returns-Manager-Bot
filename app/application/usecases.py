from dataclasses import dataclass
from datetime import datetime, timezone
from .ports import ClaimsRepoPort, WbReturnsPort, NotifierPort
from app.domain.rules import AutoRejectRule, parse_wb_dt
import logging
log = logging.getLogger("returns")
@dataclass
class ProcessClaimsResult:
    checked: int
    processed: int
    skipped_already_done: int
    errors: int

class ProcessClaimsUseCase:
    def __init__(
        self,
        wb: WbReturnsPort,
        repo: ClaimsRepoPort,
        rule: AutoRejectRule,
        default_comment: str,
        enabled: bool,
        notifier: NotifierPort | None = None,   # <-- добавили
    ):
        self._wb = wb
        self._repo = repo
        self._rule = rule
        self._default_comment = default_comment
        self._enabled = enabled
        self._notifier = notifier

    async def _notify(self, text: str) -> None:
        if self._notifier is None:
            return
        await self._notifier.notify_admins(text)

    async def run(self) -> ProcessClaimsResult:
        log.info("ProcessClaims job started (enabled=%s, delay_days=%s)", self._enabled, self._rule.delay_days)
        now = datetime.now(timezone.utc)
        data = await self._wb.get_open_claims()

        checked = processed = skipped = errors = 0

        for c in data:
            checked += 1
            claim_id = c["id"]
            created_at = parse_wb_dt(c["dt"])

            if await self._repo.was_processed(claim_id):
                skipped += 1
                continue

            if not self._enabled or not self._rule.is_due(created_at, now):
                continue

            actions: list[str] = c.get("actions", [])
            action = self._pick_reject_action(actions)
            if action is None:
                msg = f"WB Returns: не удалось обработать заявку {claim_id}: нет reject-action в actions={actions}"
                await self._repo.mark_failed(claim_id, "No reject action available", now)
                await self._notify(msg)
                errors += 1
                continue

            comment = self._default_comment if self._needs_comment(action) else None

            try:
                await self._wb.answer_claim(claim_id, action, comment)
                await self._repo.mark_done(claim_id, action, now)

                await self._notify(
                    "WB Returns: отклонена/обработана заявка\n"
                    f"- id: {claim_id}\n"
                    f"- created: {created_at.isoformat()}\n"
                    f"- action: {action}\n"
                    f"- comment: {comment or '-'}\n"
                    f"- processed_at: {now.isoformat()}"
                )
                processed += 1

            except Exception as e:
                err = f"{type(e).__name__}: {e}"
                await self._repo.mark_failed(claim_id, err, now)

                await self._notify(
                    "WB Returns: ошибка при обработке заявки\n"
                    f"- id: {claim_id}\n"
                    f"- created: {created_at.isoformat()}\n"
                    f"- action: {action}\n"
                    f"- error: {err}\n"
                    f"- at: {now.isoformat()}"
                )
                errors += 1

        # Итоговый батч-отчёт (по желанию)
        if processed or errors:
            await self._notify(
                "WB Returns: итог выполнения джобы\n"
                f"- checked: {checked}\n"
                f"- processed: {processed}\n"
                f"- skipped_already_done: {skipped}\n"
                f"- errors: {errors}\n"
                f"- at: {now.isoformat()}"
            )
        result = ProcessClaimsResult(checked, processed, skipped, errors)
        log.info("ProcessClaims job finished: checked=%s processed=%s skipped=%s errors=%s",
                 result.checked, result.processed, result.skipped_already_done, result.errors)
        return result
    def _pick_reject_action(self, actions: list[str]) -> str | None:
        # Стратегия: предпочитаем кастомный reject, иначе любой action содержащий "reject"
        # Можно расширять под ваши правила.
        for preferred in ("rejectcustom", "reject", "reject1", "rejectcc1"):
            if preferred in actions:
                return preferred
        for a in actions:
            if "reject" in a.lower():
                return a
        return None

    def _needs_comment(self, action: str) -> bool:
        # По документации comment обязателен при rejectcustom, и нужен для некоторых approve/reject вариантов. :contentReference[oaicite:14]{index=14}
        return action.lower() in {"rejectcustom", "approvecc1"}
