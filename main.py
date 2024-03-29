__version__ = '1.2'

"""              Simulador do Pin Pad 
            - app para simular um Pin Pad virtual no Android, para a captura de senha 
            - O app funciona conectado à um PDV rodando em um desktop Windows
            - A conexão com o PDV é via TCP/IP, utilizando o pacote Twisted Internet
            - A conexão é sempre 1-para-1, isto é, 1 Pin Pad para cada PDV
            - O server da conexão é o Pin Pad
            - Após a conexão, o app fica aguardando os comandos do PDV, que serão:
                - msg - exibe uma mensagem na linha de status
                - senha - exibe uma mensagem e coleta a senha
                - sair - encerra o app
                - aviso - exibem uma mensagem na tela e aguarda "x " segundos para apagar e exibir a msg padrão 
                - geral - msg padrão. exibe na linha de status sempre que o Pin Pad estiver idle
"""

# install_twisted_rector must be called before importing and using the reactor
from kivy.support import install_twisted_reactor

install_twisted_reactor()

from twisted.internet import reactor
from twisted.internet import protocol

from kivy.app import App
from kivy.clock import _usleep
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.textinput import TextInput
from kivy.uix.label import Label
from kivy.clock import Clock


class PinServer(protocol.Protocol):
    def dataReceived(self, data):
        response = self.factory.app.handle_message(data)
        #if response and self.factory.app.servico != 'senha':
        #    self.transport.write(response)
        self.factory.app.conexao = self.transport

    def message(self, message):
        self.transport.write(message)

    def connectionLost(self, reason):
        print(f"Erro na conexão com PDV {reason}")
        self.factory.app.msg.text = "Atenção !!! Erro na conexão com PDV !!!"

class PinServerFactory(protocol.Factory):
    protocol = PinServer

    def __init__(self, app):
        self.app = app

class MainApp(App):

    servico = ""
    label = None

    def build(self):

        root = self.setup_gui()
        reactor.listenTCP(50007, PinServerFactory(self))
        return root

    def setup_gui(self):
        self.last_was_operator = None
        self.last_button = None
        self.lerSenha = False
        self.lerCartao = False
        self.conexao = None
        self.servico = ''
        self.msgstatus = ''
        main_layout = BoxLayout(orientation="vertical")
        self.msg = Label(text="Pin Pad inicializado - versão 1.2\n", font_size=30,
                        )
        self.solution = TextInput(
            multiline=False, readonly=True, halign="right", font_size=50
        )
        main_layout.add_widget(self.msg)
        main_layout.add_widget(self.solution)
        buttons = [
            ["1", "2", "3"],
            ["4", "5", "6"],
            ["7", "8", "9"],
            ["#", "0", "*"],
            ["Anula", "Limpa", "Entra"],
        ]
        for row in buttons:
            h_layout = BoxLayout()
            for label in row:
                button = Button(
                    text=label,
                    pos_hint={"center_x": 0.5, "center_y": 0.5},
                )
                if label == "Anula":
                    button.background_color=(255, 0, 0)
                    button.color=(0, 0, 0)
                elif label == "Limpa":
                    button.background_color=(214, 214, 0)
                    button.color=(0, 0, 0)
                elif label == "Entra":
                    button.background_color=(0, 172, 0)
                    button.color=(0, 0, 0)
                button.bind(on_press=self.on_button_press)
                h_layout.add_widget(button)
            main_layout.add_widget(h_layout)

        return main_layout

    def on_button_press(self, instance):
        current = self.solution.text
        button_text = instance.text

        if button_text == "Limpa":
            self.solution.text = ""
        elif button_text == "Entra":
            # self.print_message(self.solution.text)
            if self.lerSenha and len(self.solution.text) > 0:
                senha = self.solution.text.encode('utf-8')
                self.conexao.write(senha)
                self.lerSenha = False
                self.msg.text = "Aguarde. Em processamento ..."
            elif self.lerCartao and len(self.solution.text) > 0:
                cartao = self.solution.text.encode('utf-8')
                self.conexao.write(cartao)
                self.lerCartao = False
                self.msg.text = "Aguarde. Em processamento ..."
            self.solution.text = ""
        elif button_text == "Anula":
            if self.lerSenha or self.lerCartao:
                msg = button_text.encode('utf-8')
                self.conexao.write(msg)
                self.lerSenha = False
                self.lerCartao = False
            self.solution.text = ""
        else:
            if self.lerCartao:
                new_text = current + self.check_cartao(button_text)
            else:
                new_text = current + button_text
            self.solution.text = new_text
        self.last_button = button_text

    def handle_message(self, msg):
        """ Trata a mensagem recebida do PDV, dependendo do código de servço"""
        msg = msg.decode('utf-8')
        # self.msg.text = "received:  {}\n".format(msg)

        if msg [0:5] == "msg  ": # Exibe a mensagem na linha de mensagens
            self.servico = "msg"
            self.msg.text = ""
            self.msg.text = msg [5:len(msg)]

        if msg [0:5] == "geral": # Primeira mensagem da conexão. Será usada como mensagem de status
            self.servico = "geral"
            self.msg.text = ""
            self.msg.text = msg [5:len(msg)]
            self.msgstatus = self.msg.text

        if msg  [0:5] == "aviso": # Exibe a mensagem na linha de mensagens por um determinado tempo
            self.servico = "aviso"
            self.msg.text = ""
            self.msg.text = msg [5:len(msg)]
            Clock.schedule_once(self.apaga_msg, 5) # programa a função que apaga a linha de msg para ser executada após
                                                   # 5 segundos da exibição da msg

        if msg  [0:5] == "senha": # Exibe a mensagem na linha de mensagens e le a senha
            self.servico = "senha"
            self.msg.text = ""
            self.msg.text = msg [5:len(msg)]
            self.solution.password=True
            self.lerSenha = True

        if msg  [0:5] == "card ": # Exibe a mensagem na linha de mensagens e le o número do cartão
            self.servico = "cartao"
            self.msg.text = ""
            self.msg.text = msg [5:len(msg)]
            self.solution.password=False
            self.lerCartao = True

        if msg  [0:5] == "sair ": # Encerra o Pin Pad
            self.servico = "sair"
            self.msg.text = ""
            self.msg.text = "Encerrando ..."
            app.stop()
        # self.msg.text += "responded: {}\n".format(msg)
        return msg.encode('utf-8')

    def print_message(self, msg):
        self.msg.text = "{}\n".format(msg)

    def apaga_msg(self, dt):
        """ Função chamada via evento de callback, para limpor a linha de mensagem, X segundos após a exibição
            e exibir a msg de status """
        self.msg.text = self.msgstatus

    def check_cartao(self, caracter):
        """ Consiste e formata o número do cartão: 9999.9999.9999.9999.
            Retorna a nova substring, e se a string de entrada é válida ou não
            """

        # print(caracter)

        if not caracter.isdecimal() or len(self.solution.text + caracter) > 19:
            return ''
        elif len(self.solution.text + caracter) == 4 or \
                len(self.solution.text + caracter) == 9 or \
                len(self.solution.text + caracter) == 14:
            return caracter + "."
        else:
            return caracter

if __name__ == "__main__":

    app = MainApp()

    app.run()