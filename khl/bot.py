from khl.command.session import Session
from typing import Any, Dict, List, Union

from khl import BaseClient, Cert, TextMsg, user
from khl.command import AppCommand, Command, parser

from .hardcoded import API_URL
from .webhook import WebhookClient
from .websocket import WebsocketClient


class Bot:
    """
    Entity that interacts with user/environment
    """
    def __init__(self,
                 *,
                 cmd_prefix: Union[List[str], str, tuple] = ('!', '！'),
                 cert: Cert,
                 compress: bool = True,
                 **kwargs):
        """
        Constructor of Bot

        :param cmd_prefix: accepted prefix for msg to be a command
        :param net_client: http connector/handler used, usually :class:`khl.webhook.WebhookClient`
        """
        self.cmd_prefix = [i for i in cmd_prefix]
        if cert.type == cert.Types.WEBHOOK:
            args = {'cert': cert, 'compress': compress}

            port = kwargs.get('port')
            if port is not None:
                args['port'] = port

            route = kwargs.get('route')
            if route is not None:
                args['route'] = route
            self.net_client: BaseClient = WebhookClient(**args)
        else:
            self.net_client: BaseClient = WebsocketClient(cert=cert,
                                                          compress=compress)

        self.__cmd_list: Dict[str, Command] = {}

    def add_command(self, cmd: Command):
        # if not isinstance(cmd, BaseCommand):
        #     raise TypeError('not a Command')
        if cmd.trigger in self.__cmd_list.keys():
            raise ValueError('Command Name Exists')
        self.__cmd_list[cmd.trigger] = cmd
        cmd.set_bot(self)

    def command(self, name: str):
        def decorator(func):
            cmd = AppCommand()
            cmd.trigger = name
            cmd.func = func
            self.add_command(cmd)

        return decorator

    def gen_msg_handler_preview(self):
        async def msg_handler_preview(d: Dict[Any, Any]):
            """
            docstring
            """
            print(d)
            res = parser(d, self.cmd_prefix)
            if isinstance(res, TextMsg):
                return None
            (command_str, args, msg) = res
            inst = self.__cmd_list.get(command_str)
            if inst:
                result = inst.execute(Session(inst, command_str, args, msg))
                return await result

        return msg_handler_preview

    async def send(self,
                   channel_id: str,
                   content: str,
                   *,
                   quote: str = '',
                   object_name: int = TextMsg.Types.KMD,
                   nonce: str = '') -> Any:
        data = {
            'channel_id': channel_id,
            'content': content,
            'object_name': object_name,
            'quote': quote,
            'nonce': nonce
        }
        return await self.net_client.send(
            f'{API_URL}/channel/message?compress=0', data)

    async def user_grant_role(self, user_id: str, guild_id: str,
                              role_id: int) -> Any:
        return await self.net_client.send(
            f'{API_URL}/guild-role/grant?compress=0', {
                'user_id': user_id,
                'guild_id': guild_id,
                'role_id': role_id
            })

    def run(self):
        self.net_client.on_recv_append(self.gen_msg_handler_preview())
        self.net_client.run()
