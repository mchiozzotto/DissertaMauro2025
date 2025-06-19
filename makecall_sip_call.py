
# Programa Python makecall.py associado ao configurador (INI) sip_config.ini ou makecall.ini

#!/usr/bin/env python3
import pjsua2 as pj
import time
import logging
import subprocess
import os
import socket
import gc
import configparser
from threading import Lock

# Configuração do nível de logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s: %(message)s")


class MyCall(pj.Call):
    """Classe para gerenciar estados de chamadas SIP."""
    def __init__(self, account):
        pj.Call.__init__(self, account)

    def onCallState(self, prm):
        """Callback chamado quando o estado da chamada muda."""
        try:
            ci = self.getInfo()
            logging.info(f"Estado da chamada: {ci.stateText}, código de status: {ci.lastStatusCode}")
            if ci.state == pj.PJSIP_INV_STATE_DISCONNECTED:
                logging.info("Chamada desconectada.")
        except pj.Error as e:
            logging.error(f"Erro ao obter estado da chamada: {e}")

    def onCallMediaState(self, prm):
        """Callback chamado quando o estado da mídia da chamada muda."""
        try:
            ci = self.getInfo()
            for mi in ci.media:
                if mi.type == pj.PJMEDIA_TYPE_AUDIO and mi.status == pj.PJSUA_CALL_MEDIA_ACTIVE:
                    logging.info(f"Stream de áudio ativo na porta {mi.streamInfo.port}")
        except pj.Error as e:
            logging.error(f"Erro ao verificar estado de mídia: {e}")


class SipCall:
    """Classe para gerenciar chamadas SIP usando library PJSUA2."""
    def __init__(self, config_file="sip_config.ini"):
        """Inicializa o endpoint SIP (ramail) e configura a conta a partir do arquivo de configuração."""
        # Ler arquivo de configuração
        config = configparser.ConfigParser()
        if not os.path.exists(config_file):
            raise FileNotFoundError(f"Arquivo de configuração {config_file} não encontrado.")
        config.read(config_file)

        # Extrair configurações
        self.username = config.get('SIP', 'username')
        self.password = config.get('SIP', 'password')
        self.server = config.get('SIP', 'server')
        self.use_tls = config.getboolean('SIP', 'use_tls')
        self.dest_uri = config.get('SIP', 'dest_uri')
        self.media_port = config.getint('Transport', 'media_port')
        self.sip_port = config.getint('Transport', 'sip_port')
        self.enable_audio = config.getboolean('Audio', 'enable_audio')
        self.opus_enabled = config.getboolean('Audio', 'opus_enabled')
        self.opus_bitrate = config.getint('Audio', 'opus_bitrate')
        self.opus_complexity = config.getint('Audio', 'opus_complexity')
        self.opus_cbr = config.getboolean('Audio', 'opus_cbr')
        self.opus_fec = config.getboolean('Audio', 'opus_fec')
        self.opus_max_playback_rate = config.getint('Audio', 'opus_max_playback_rate')
        self.max_calls = config.getint('Endpoint', 'max_calls')
        self.thread_count = config.getint('Endpoint', 'thread_count')
        self.log_level = config.getint('Endpoint', 'log_level')
        self.rtp_port = config.getint('Endpoint', 'rtp_port')
        self.local_ip_config = config.get('Network', 'local_ip', fallback='auto')

        # Validar as configurações obrigatórias
        if not all([self.username, self.password, self.server, self.dest_uri]):
            raise ValueError("Username, password, server e dest_uri devem ser fornecidos no arquivo de configuração.")

        self.lock = Lock()
        self.ep = pj.Endpoint()
        logging.info("Criando endpoint...")
        self.ep.libCreate()

        # Configuração do endpoint (Ramal) 
        ep_cfg = pj.EpConfig()
        ep_cfg.uaConfig.threadCnt = self.thread_count
        ep_cfg.uaConfig.maxCalls = self.max_calls
        ep_cfg.logConfig.level = self.log_level
        ep_cfg.logConfig.cb = self.log_cb
        ep_cfg.medConfig.noAudio = not self.enable_audio
        ep_cfg.medConfig.sndAutoCloseTime = 0
        ep_cfg.medConfig.ipv6Use = 0  # Força IPv4
        ep_cfg.medConfig.rtpPort = self.rtp_port

        # Logar interfaces de rede
        try:
            interfaces = os.listdir('/sys/class/net/')
            logging.info(f"Interfaces de rede disponíveis: {interfaces}")
            for iface in interfaces:
                addr = subprocess.check_output(f"ip addr show {iface} | grep inet | awk '{{print $2}}'", shell=True, text=True).strip()
                logging.info(f"Interface {iface}: {addr}")
        except Exception as e:
            logging.warning(f"Erro ao listar interfaces de rede: {e}")

        logging.info("Inicializando endpoint ramal...")
        self.ep.libInit(ep_cfg)

        # Verificar PulseAudio do Linux:
        pulseaudio_running = False
        pulseaudio_error = None
        if self.enable_audio:
            try:
                result = subprocess.run(["pactl", "info"], capture_output=True, text=True, timeout=5)
                if result.returncode == 0:
                    logging.info("PulseAudio está rodando no sistema.")
                    logging.info(f"PulseAudio server: {result.stdout.splitlines()[0]}")
                    pulseaudio_running = True
                else:
                    pulseaudio_error = result.stderr.strip()
            except subprocess.CalledProcessError as e:
                pulseaudio_error = str(e)
            except subprocess.TimeoutExpired:
                pulseaudio_error = "Timeout ao verificar PulseAudio"

            if not pulseaudio_running:
                logging.warning(f"PulseAudio não está rodando ou não está acessível: {pulseaudio_error}")
                pulse_server = os.environ.get("PULSE_SERVER", "não definido")
                logging.info(f"PULSE_SERVER configurado como: {pulse_server}")

        # Configurar dispositivo de áudio
        aud_mgr = self.ep.audDevManager()
        audio_configured = False
        self.use_audio = self.enable_audio
        dev_count = aud_mgr.getDevCount()
        logging.info(f"Dispositivos de áudio disponíveis: {dev_count}")

        if dev_count > 0:
            logging.info("Detalhes dos dispositivos de áudio:")
            for i in range(dev_count):
                try:
                    dev_info = aud_mgr.getDevInfo(i)
                    logging.info(f"Dispositivo {i}: {dev_info.name}, inputCount: {dev_info.inputCount}, outputCount: {dev_info.outputCount}")
                except pj.Error as e:
                    logging.warning(f"Erro ao obter informações do dispositivo {i}: {e}")

        if self.enable_audio and pulseaudio_running:
            # Tentar configurar PulseAudio automaticamente
            pulseaudio_idx = None
            for i in range(dev_count):
                try:
                    dev_info = aud_mgr.getDevInfo(i)
                    if 'pulseaudio' in dev_info.name.lower() and dev_info.inputCount > 0 and dev_info.outputCount > 0:
                        pulseaudio_idx = i
                        logging.info(f"PulseAudio detectado automaticamente: índice {i} ({dev_info.name})")
                        break
                except pj.Error as e:
                    logging.debug(f"Erro ao verificar dispositivo {i}: {e}")

            if pulseaudio_idx is not None:
                try:
                    aud_mgr.setPlaybackDev(pulseaudio_idx)
                    aud_mgr.setCaptureDev(pulseaudio_idx)
                    logging.info(f"Dispositivo de áudio configurado: PulseAudio (índice {pulseaudio_idx})")
                    audio_configured = True
                except pj.Error as e:
                    logging.warning(f"Erro ao configurar PulseAudio (índice {pulseaudio_idx}): {e}")

        if not audio_configured and dev_count > 0 and self.enable_audio:
            # Fallback para outro dispositivo de áudio
            for i in range(dev_count):
                try:
                    dev_info = aud_mgr.getDevInfo(i)
                    if dev_info.inputCount == 0 or dev_info.outputCount == 0:
                        logging.warning(f"Dispositivo {dev_info.name} (índice {i}) não suporta entrada ou saída de áudio.")
                        continue
                    aud_mgr.setPlaybackDev(i)
                    aud_mgr.setCaptureDev(i)
                    logging.info(f"Dispositivo de áudio configurado: {dev_info.name} (índice {i})")
                    audio_configured = True
                    break
                except pj.Error as e:
                    logging.warning(f"Erro ao configurar dispositivo de áudio (índice {i}): {e}")

        if not audio_configured and self.enable_audio:
            logging.warning("Não foi possível configurar áudio. Prosseguindo sem mídia de áudio.")
            self.use_audio = False
            ep_cfg.medConfig.noAudio = True

        # Configurar os CODECs - prioridade OPUS (se áudio estiver habilitado)
        if self.use_audio and self.opus_enabled:
            try:
                codecs = self.ep.codecEnum2()
                logging.info("Codecs disponíveis:")
                for codec in codecs:
                    logging.info(f"Codec: {codec.codecId}, Prioridade: {codec.priority}")
                self.ep.codecSetPriority("opus/48000/2", 255)
                logging.info("Codec Opus habilitado com prioridade máxima.")
                opus_param = pj.CodecParam()
                opus_param.info.codecId = "opus/48000/2"
                opus_param.setting.avgBitrate = self.opus_bitrate
                opus_param.setting.complexity = self.opus_complexity
                opus_param.setting.cbr = self.opus_cbr
                opus_param.setting.fec = self.opus_fec
                opus_param.setting.maxPlaybackRate = self.opus_max_playback_rate
                self.ep.codecSetParam("opus/48000/2", opus_param)
                logging.info("Parâmetros do CODEC Opus configurados.")
            except pj.Error as e:
                logging.warning(f"Erro ao configurar codec Opus: {e}. Verifique se o PJSIP suporta Opus.")

        # Obter endereço IP local dinamicamente
        local_ip = self.get_local_ip()
        logging.info(f"Endereço IP local detectado: {local_ip}")

        # Configuração do transporte de mídia
        med_transport_cfg = pj.TransportConfig()
        med_transport_cfg.port = self.media_port
        med_transport_cfg.boundAddr = local_ip
        logging.info("Criando transporte de mídia UDP...")
        self.med_transport = self.ep.transportCreate(pj.PJSIP_TRANSPORT_UDP, med_transport_cfg)

        # Configuração do transporte SIP
        transport_cfg = pj.TransportConfig()
        transport_cfg.port = self.sip_port
        transport_cfg.boundAddr = local_ip
        transport_type = pj.PJSIP_TRANSPORT_TLS if self.use_tls else pj.PJSIP_TRANSPORT_UDP
        if self.use_tls:
            transport_cfg.tlsConfig.verifyServer = True
        logging.info(f"Criando transporte SIP {'TLS' if self.use_tls else 'UDP'}...")
        self.transport = self.ep.transportCreate(transport_type, transport_cfg)

        logging.info("Iniciando a biblioteca...")
        self.ep.libStart()

        # Configuração da conta SIP
        acc_cfg = pj.AccountConfig()
        acc_cfg.idUri = f"sips:{self.username}@{self.server}" if self.use_tls else f"sip:{self.username}@{self.server}"
        acc_cfg.regConfig.registrarUri = f"sips:{self.server}" if self.use_tls else f"sip:{self.server}"
        cred = pj.AuthCredInfo("digest", self.server, self.username, 0, self.password)
        acc_cfg.sipConfig.authCreds.append(cred)
        acc_cfg.sipConfig.contactParams = ";transport=udp"
        acc_cfg.natConfig.sdpNatRewrite = True
        acc_cfg.natConfig.viaRewrite = True
        acc_cfg.natConfig.contactRewrite = True

        logging.info("Criando conta SIP...")
        self.account = pj.Account()
        self.account.create(acc_cfg)

        logging.info("Aguardando registro do endpoint...")
        self.wait_for_registration()
        self.call = None

    def get_local_ip(self):
        """Obtém o endereço IP local da máquina."""
        # Verificar se um IP estático foi configurado
        if self.local_ip_config.lower() != 'auto':
            logging.info(f"Usando IP estático configurado: {self.local_ip_config}")
            return self.local_ip_config

        # Método primário: socket  - Revisar endereços IP no Teste LAB, socket era feito separado:
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.settimeout(0)
            s.connect(('8.8.8.8', 80))
            local_ip = s.getsockname()[0]
            s.close()
            logging.info("IP obtido via socket.")
            return local_ip
        except Exception as e:
            logging.warning(f"Erro ao obter IP via socket: {e}")

        # Fallback 1: ip addr show
        try:
            interfaces = os.listdir('/sys/class/net/')
            logging.info(f"Interfaces encontradas: {interfaces}")
            for iface in interfaces:
                if iface != 'lo':
                    try:
                        addr = subprocess.check_output(
                            f"ip addr show {iface} | grep inet | awk '{{print $2}}' | cut -d'/' -f1",
                            shell=True, text=True
                        ).strip()
                        if addr:
                            logging.info(f"IP encontrado na interface {iface}: {addr}")
                            return addr
                    except subprocess.CalledProcessError as e:
                        logging.debug(f"Sem endereço IPv4 na interface {iface}: {e}")
            logging.warning("Nenhum IP válido encontrado via ip addr show.")
        except Exception as e:
            logging.warning(f"Erro ao listar interfaces via ip addr show: {e}")

        # Fallback 2: ifconfig (para sistemas sem iproute2)
        try:
            ifconfig_output = subprocess.check_output("ifconfig", shell=True, text=True)
            for line in ifconfig_output.splitlines():
                if 'inet ' in line and '127.0.0.1' not in line:
                    addr = line.split()[1]
                    if addr:
                        logging.info(f"IP encontrado via ifconfig: {addr}")
                        return addr
            logging.warning("Nenhum IP válido encontrado via ifconfig.")
        except Exception as e:
            logging.warning(f"Erro ao obter IP via ifconfig: {e}")

        # Fallback 3: /proc/net (método minimalista)
        try:
            with open('/proc/net/fib_trie', 'r') as f:
                for line in f:
                    if '32 host LOCAL' in line:
                        addr = line.strip().split()[0]
                        if addr and addr != '127.0.0.1':
                            logging.info(f"IP encontrado via /proc/net/fib_trie: {addr}")
                            return addr
            logging.warning("Nenhum IP válido encontrado via /proc/net.")
        except Exception as e:
            logging.warning(f"Erro ao obter IP via /proc/net: {e}")

        # Último recurso: retornar 0.0.0.0
        logging.warning("Nenhum IP válido encontrado. Usando 0.0.0.0.")
        return "0.0.0.0"

    def log_cb(self, level, str_data, len_data):
        """Callback para logs do PJSIP."""
        logging.info(f"PJSIP: {str_data.strip()}")

    def wait_for_registration(self, timeout=10):
        """Aguarda o registro da conta SIP no Servidor SIP ."""
        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                acc_info = self.account.getInfo()
                if acc_info.regStatus == 200:
                    logging.info("Registro concluído com sucesso.")
                    return
                time.sleep(0.1)
            except pj.Error as e:
                logging.error(f"Erro ao verificar registro: {e}")
                break
        logging.warning("Timeout aguardando registro.")

    def make_call(self, dest_uri=None):
        """Inicia o Makecall - uma chamada SIP."""
        with self.lock:
            if not dest_uri:
                dest_uri = f"sip:{self.dest_uri}"
            if self.call and self.call.isActive():
                logging.warning("Chamada ativa detectada. Encerrando antes de iniciar nova chamada...")
                self.terminate_call()

            self.call = MyCall(self.account)
            call_param = pj.CallOpParam(True)
            call_param.opt.audioCount = 1 if self.use_audio else 0
            call_param.opt.videoCount = 0
            if not self.use_audio:
                call_param.opt.flag |= pj.PJSUA_CALL_NO_SDP_OFFER
            logging.info(f"Iniciando chamada para {dest_uri}")
            try:
                self.call.makeCall(dest_uri, call_param)
            except pj.Error as e:
                logging.error(f"Erro ao iniciar chamada: {e}")
                self.call = None

    def run(self):
        """Executa o loop de eventos para gerenciar a chamada."""
        logging.info("Rodando loop de eventos...")
        self.make_call()
        try:
            while self.call is not None and self.call.isActive():
                self.ep.libHandleEvents(10)
                time.sleep(0.03)
        except Exception as e:
            logging.error(f"Erro no loop de eventos: {e}")
        finally:
            self.terminate()

    def terminate_call(self):
        """Encerra a chamada ativa, se houver."""
        with self.lock:
            if self.call is not None and self.call.isActive():
                try:
                    call_param = pj.CallOpParam()
                    call_param.statusCode = pj.PJSIP_SC_DECLINE
                    self.call.hangup(call_param)
                    time.sleep(0.5)  # Espera para eventos pendentes
                    logging.info("Chamada encerrada com sucesso.")
                except pj.Error as e:
                    logging.warning(f"Erro ao encerrar chamada: {e}")
                finally:
                    self.call = None

    def terminate(self):
        """Encerra a biblioteca e fecha o transporte."""
        logging.info("Encerrando biblioteca...")
        self.terminate_call()
        try:
            # Processar eventos pendentes após encerrar chamada
            logging.info("Processando eventos pendentes após chamada...")
            for _ in range(5):
                self.ep.libHandleEvents(10)
                time.sleep(0.1)
            if self.med_transport:
                self.ep.transportClose(self.med_transport)
                logging.info("Transporte de mídia fechado.")
            if self.transport:
                self.ep.transportClose(self.transport)
                logging.info("Transporte SIP fechado.")
            # Processar eventos após unregistration
            logging.info("Processando eventos finais antes de destruir...")
            for _ in range(5):
                self.ep.libHandleEvents(10)
                time.sleep(0.1)
            # Forçar liberação do objeto de chamada
            if self.call is not None:
                logging.info("Liberando objeto de chamada...")
                del self.call
                self.call = None
            # Forçar coleta de lixo
            logging.info("Forçando coleta de lixo...")
            gc.collect()
            # Destruir biblioteca
            self.ep.libDestroy()
            logging.info("Biblioteca PJSUA2 destruída.")
        except pj.Error as e:
            logging.error(f"Erro ao destruir biblioteca: {e}")


if __name__ == "__main__":
    sip_call = None
    try:
        sip_call = SipCall(config_file="sip_config.ini")
        sip_call.run()
    except KeyboardInterrupt:
        logging.info("Interrupção pelo usuário detectada.")
        if sip_call:
            sip_call.terminate()
    except Exception as e:
        logging.error(f"Erro inesperado: {e}")
        if sip_call:
            sip_call.terminate()
