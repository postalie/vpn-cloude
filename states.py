from aiogram.fsm.state import State, StatesGroup

class PromoStates(StatesGroup):
    waiting_for_code = State()

class AdminStates(StatesGroup):
    waiting_for_promo_data = State() # формат: код сумма активации
    waiting_for_discount_data = State() # формат: код процент активации
    waiting_for_keys = State() # Загрузка ключей
    waiting_for_server_nodes = State() # Загрузка общих узлов
    waiting_for_user_id_clear = State() # ID для удаления подписки
    waiting_for_user_id_gift = State()  # ID для выдачи подписки
    waiting_for_node_name = State() # Новое имя для сервера
    waiting_for_node_data = State() # Новый ключ для сервера
    waiting_for_user_limit = State() # Лимит устройств для юзера
    waiting_for_user_limit = State() # Лимит устройств для юзера
    waiting_for_user_balance = State() # Баланс для юзера
    waiting_for_broadcast_text = State() # Текст рассылки
    waiting_for_broadcast_confirm = State() # Подтверждение рассылки
    waiting_for_ref_data = State() # формат: код бонус комментарий

class BuyStates(StatesGroup):
    waiting_for_discount = State()

class PayStates(StatesGroup):
    waiting_for_amount = State()
