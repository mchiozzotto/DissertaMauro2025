#!/usr/bin/env python
# coding: utf-8
#
# Programa socket CLiente UDP para falar com Raspberry PI 3:

import socket
import os
os.getcwd()

# Abrir o Arquivo RESULT.TXT e enviar o resultado para o Raspberry:


BUFFER_SIZE = 51
file_path = "result.txt"

try:
    #Abra o arquivo em mode de leitura Binario:
    with open(file_path,'rb') as file:
    # Ler os primeiros N bytes do RESULT.txt:
        data2 = file.read(BUFFER_SIZE)
        #print(type(data2))
        data2=data2.decode()
        data2_sempontos = data2.replace('.','')
        print(f"{data2_sempontos}")
except FileNotFoundError:
    print(f"Erro Arquivo: O arquivo {file_path} nao foi encontrado.")
    exit(1)
    
# Define Endereco IP do Server Raspberry e Porta:

server_ip = "192.168.15.100"


server_port = 51579

# Cria um socket UDP:

client_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

message = "Boa tarde Servidor RaspberryPI3"

# Enviar a msg acima para p servidor:
#client_socket.sendto(message.encode(), (server_ip,server_port))

client_socket.sendto(data2_sempontos.encode(), (server_ip,server_port))

# Recebe a Resposta do Server Raspberry:

data, addr = client_socket.recvfrom(100)  # Buffer de 100 bytes
print(f"A resposta do Raspberry PI eh: {data.decode()}")
data, addr = client_socket.recvfrom(100)  # Buffer de 100 bytes
print(f"Finalmente.... {data.decode()}")

# Por fim, fecha o socket:
client_socket.close()

# Fim do programa Socket Client !




