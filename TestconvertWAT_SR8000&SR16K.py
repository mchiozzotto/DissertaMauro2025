#!/usr/bin/env python
# coding: utf-8

# Programa rev 5 SET/24 update com 2 arquivos .WAV degradados gravados: SR=8.000 Hz e SR =16.000Hz
# assim, considerando "Arquivo1(Entrada) e "Arquivo2(Entrada 2)":

import numpy as np
import pandas as pd
import os
import time
import librosa
import librosa.display
import IPython.display as ipd
import soundfile as sf

os.getcwd()

get_ipython().run_cell_magic('bash', '', 'cd ..\ncd grava\n#!/bin/bash\ndeclare -A var1\ndeclare -A var2\ncd ../grava1\nfind . -name "Testsipn*.wav" > ../grava/tipofile.txt\ncd ../grava\nvar1=$(cat tipofile.txt | wc -c)\nvar2=$(cat tipofile1| wc -c)\nwhile (($var1!=$var2));\ndo\n   cd ../grava1\n   find . -name "Testsipn*.wav" > ../grava/tipofile.txt\n   cd ../grava\n   var1=$(cat tipofile.txt |wc -c)\n   echo "Nao encontrei WAV file"\ndone;\narquivo1=$(cat tipofile.txt | tr -d \'./wav\')\necho "Chegou o WAV" $arquivo1".wav"\n')
folder = '/home/maurochiozzotto/Documents/ITUTP862/grava1'
awav = os.listdir(folder)
awav = str(awav)  # Transforma uma List em string de chars
awav=(awav.replace('[',''))
awav=(awav.replace(']',''))
awav=(awav.replace('\'',''))
arq1 = ('/home/maurochiozzotto/Documents/ITUTP862/grava1/')+(awav)
arq3 = ('/home/maurochiozzotto/Documents/ITUTP862/grava1/')+(awav)

y,sr = librosa.load(arq1, sr=8000) # Convert Arquivo gravado para  SR 8.000Hz
sr
yy,sr = librosa.load(arq3,sr=16000) # Em "yy" convert arquivo gravado para SR 16.000 Hz
sr
arq2 = (arq1.replace('.wav','')) +('80')+('.wav')
arq2 = (arq2.replace('grava1','grava2'))
print (arq2)  # Move para a Pasta Grava2 o arq2 com SR=8000 Hz mantendo a pasta 'grava1' soh com um arquivo .wav
arq4 = (arq3.replace('.wav','')) +('16k')+('.wav')
arq4 = (arq4.replace('grava1','grava2'))
#print (arq4)# Move para a Pasta Grava2 o arq4 com SR=16000 Hz mantendo a pasta 'grava1' soh com um arquivo .wav

sf.write(arq2,y,samplerate=8000)   # Arquivo (arq2) gerado para SR = 8.000 Hz
sf.write(arq4,yy,samplerate=16000)  # Arquivo (arq4) gerado para SR =16.000 Hz

# FIM da Rotina conversora e grava arquivo "TestsipnXX80.wav ou ...sipnXX16.wav"
# no folder: /Documents/ITUTP862/grava2

# Modulo PESQ Adicionado abaixo:
# xx,sr = librosa.load('/home/mchiozzo/Documents/ITUTP862/grava2/Testsipn0116.wav', sr=None)
# In[323]:
# Alterei abaixo new: Mtestlong17s8.wav visto que o rating da Pesq melhorou SET/24 separei medições com audios
# Originais com SR = 8.000 Hz e SR = 16.000 Hz, assim posso escolher de forma equivalente ao SR do audio degradado,
# 2024 - Audio em Ingles =>  alterado FILE ORIGEM para mais longo, voz masculina e silencio 17seg: Mtestlong17s8.wav:
get_ipython().run_cell_magic('bash', '', 'cd ..\ncd grava2\ncp Testsipn0180.wav ..\ncp Testsipn0116k.wav ..\ncd ..\n#!/bin/bash#\n#function fpesq\n#{\n#   #!/bin/bash\n   echo "Inicio da pesq ITUTP862 e WB salva em 2 arquivos:"\n   ./pesq +8000 Mtestlong17s8.wav Testsipn0180.wav| tee resut.txt   # Out24 alterei para 8.000 Hz Original audio\n   ./pesq +16000 +wb Mtestlong17s16.wav Testsipn0116k.wav| tee resutwb.txt  \n#   return 0\n#}\n')

# Por fim, eu transfiro o Resultado das 2 PESQs (nb e wb) para os arquivos "ResultA e ..wA.txt" abaixo de uma linha somente:
# E concatena resultado Final para a Pasta aguardada pelo outro Programa JVoIP ou PJSIP
# Para:  " ~~/ITUTP862/grava2/result.txt", vide abaixo:

get_ipython().run_cell_magic('bash', '', 'cd ..\ntail -n 1 resut.txt > resultA.txt\ntail -n 1 resutwb.txt > resultwA.txt\ncat resultA.txt resultwA.txt > result.txt\ncat result.txt\ncp result.txt grava2/result.txt\ncat resultFinal.txt result.txt > resultFinal1.txt\ncp resultFinal1.txt resultFinal.txt\ncat resultFinal.txt\n')

# Por fim, clean Folder: ´grava1´ para o próximo Loop de Medições e copy
# audio degradado originário das medições para o ""~~/ITUTP862/grava2":

get_ipython().run_cell_magic('bash', '', 'cd ..\ncd grava1\ncp Testsip*.wav ../grava2/Testsipn01.wav\nrm Testsipn0*.wav\n')

print("Tecla TAB pressionada -> FIM do programa -TestconvertSR8000&SR16000")

# Final do Programa obtenção valores PESQ obtendo
# duas comparaçoes das Sample Rate: SR=8000 Hz (arq2) + SR=16000Hz (arq4)
# Usa "Result.txt" na transmissão socket UDP para o IoT Raspberry Pi 3 fim do ciclo.

