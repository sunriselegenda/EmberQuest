"""Точка входа. Запуск: python main.py"""
import os
os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = '1'
from ember_quest.game import main

if __name__ == '__main__':
    main()
