# dispatcher.py
from aiogram import Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage

# Initialize dispatcher with memory storage
storage = MemoryStorage()
dp = Dispatcher(storage=storage)
