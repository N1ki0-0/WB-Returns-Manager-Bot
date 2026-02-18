# tests/test_supply_phones.py
import os
import pytest
import httpx

@pytest.mark.skipif(
    not os.getenv("SUPPLY_ID") or not os.getenv("WB_API_TOKEN"),
    reason="Укажите SUPPLY_ID и WB_API_TOKEN в переменных окружения"
)
def test_print_supply_phones():
    """
    Тест обращается к существующей поставке WB через новый endpoint,
    получает список заказов и выводит телефоны и товары в читаемом виде.
    """
    supply_id = os.getenv("SUPPLY_ID")
    token = os.getenv("WB_API_TOKEN")
    headers = {"Authorization": token} if token else {}

    url = f"https://marketplace-api.wildberries.ru/api/v3/supplies/{supply_id}"

    try:
        r = httpx.get(url, headers=headers, timeout=30.0)
        r.raise_for_status()
    except httpx.HTTPStatusError as e:
        pytest.fail(f"Ошибка запроса к WB API: {e.response.status_code} {e.response.text}")
    except Exception as e:
        pytest.fail(f"Ошибка запроса: {e}")

    data = r.json()

    # Предположим, что заказы находятся в data['orders'] или data['items']
    orders = data.get("orders") or data.get("items") or []

    if not orders:
        print(f"Поставки {supply_id} нет заказов.")
        return

    print(f"=== Поставкa {supply_id} — список телефонов и товаров ===")
    for o in orders:
        phone = o.get("phone") or o.get("recipientPhone") or "N/A"
        product_name = o.get("offerName") or o.get("subjectName") or "N/A"
        qty = o.get("quantity", 1)
        print(f"{phone}: {product_name} — {qty} шт")
    print("=== Конец списка ===")
