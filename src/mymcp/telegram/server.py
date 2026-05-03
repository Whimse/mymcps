
from ..server import MCPServer
from .telegram import TelegramHelper

def run():

    tools = []

    telegram_interface = TelegramHelper()

    tools += [
        telegram_interface.get_updates,
        telegram_interface.send_message,
        telegram_interface.send_chat_action,
    ]
    
    server = MCPServer()
    server.start(tools)
