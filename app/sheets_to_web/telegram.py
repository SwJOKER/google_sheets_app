import asyncio
import logging
import os
from aiogram.fsm.storage.redis import RedisStorage
from aioredis import Redis
from asgiref.sync import sync_to_async
from aiogram import Bot, Dispatcher, Router, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from django.conf import settings

router = Router()
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'app.settings')
bot = Bot(settings.TELEGRAM_BOT_TOKEN, parse_mode='HTML')


class RouterStates(StatesGroup):
    check_user = State()
    main = State()
    add_subscribtions = State()
    select_add_subscriptions = State()
    del_subscribtions = State()
    select_del_subscriptions = State()


async def send_message(channel_id: int, text: str):
    await bot.send_message(channel_id, text)


@router.message(Command(commands=['start']))
async def cmd_start(message: types.Message, state: FSMContext):
    from .models import TelegramSubscriber
    user = await sync_to_async(TelegramSubscriber.objects.filter(chat_id=message.chat.id).first)()
    if not user:
        await state.set_state(RouterStates.check_user)
        return await message.answer('Enter check code')
    else:
        return await message.answer('You are already subscribed. For unsubscribe enter /stop')


@router.message(Command(commands=['stop']))
async def cmd_stop(message: types.Message, state: FSMContext):
    from .models import TelegramSubscriber

    user = await sync_to_async(TelegramSubscriber.objects.filter(chat_id=message.chat.id).first)()
    if not user:
        return await message.answer('You are not subscribed yet')
    else:
        await sync_to_async(user.delete)()
        return await message.answer('You are successfuly unsubscribed')


@router.message(RouterStates.check_user)
async def check_user(message: types.Message, state: FSMContext):
    from .models import TelegramSubscriber, Sheet

    if message.text.strip() == os.getenv('CLIENT_TELEGRAM_CODE'):
        # m2m field provides posibility make bot cleverer. Now it not used
        sheets = await sync_to_async(Sheet.objects.all().only)('key')
        sheets_ids = list()
        async for s in sheets:
            sheets_ids.append(s.key)
        obj = await sync_to_async(TelegramSubscriber.objects.create)(chat_id=message.chat.id)
        if await sync_to_async(sheets.first)():
            await sync_to_async(obj.sheets.add)(*sheets_ids)
        await state.clear()
        await message.answer('You will receive infromation about expired deliveries')
    else:
        await state.clear()
        await message.answer('Password incorrect. Try again from /start command')


async def send_notify_main():
    from .models import Sheet, Order, TelegramSubscriber
    from django.core.cache import cache

    while True:
        await asyncio.sleep(5)
        keys = await sync_to_async(cache.get)('expired_sheets_keys')
        if keys:
            expired_orders_full = list()
            sheets = await sync_to_async(Sheet.objects.filter)(key__in=keys)
            async for sheet in sheets:
                expired_orders_numbers = await sync_to_async(cache.get)(f'expired_{sheet.key}')
                expired_orders_full.extend(expired_orders_numbers)
               # There is a way to make clever bot with capacity choosing sheets for subscribe
               # async for subscriber in sheet.subscribers.all():
                async for subscriber in TelegramSubscriber.objects.all():
                    href = f'<a href="https://docs.google.com/spreadsheets/d/{sheet.key}/">{sheet.name}</a>'
                    text = f'In Google Sheet:\n' \
                           f'{href}\n' \
                           f'Next orders delivery expired:\n' \
                           f'{expired_orders_numbers}'
                    await send_message(channel_id=subscriber.chat_id, text=text)
                await sync_to_async(cache.delete)(f'expired_{sheet.key}')
            # update orders delivery status
            await sync_to_async(Order.objects.filter(order_index__in=expired_orders_full).update)(
                delivery_expired=True)
            await sync_to_async(cache.delete)('expired_sheets_keys')


async def telegram_main():
    from django.conf import settings
    logging.basicConfig(level="DEBUG")
    redis = await Redis(host=settings.REDIS_HOST, port=settings.REDIS_PORT, db=2)
    dp = Dispatcher(storage=RedisStorage(redis))
    router.bot = bot
    dp.include_router(router)
    await dp.start_polling(bot)


def init_django():
    import django
    django.setup()


def start():
    init_django()
    loop = asyncio.get_event_loop()
    loop.create_task(send_notify_main())
    loop.create_task(telegram_main())
    loop.run_forever()


