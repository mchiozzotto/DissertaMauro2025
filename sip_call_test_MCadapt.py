#!/usr/bin/env python3
import pjsua2 as pj
import time
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s: %(message)s")

# Programa PJSIP/PJSUA em Python Mauro alterado FEV/2015 para o padrão FreePBX15 e LAB
# Make Call do PJSIP usando biblioteca PJSUA

class MyCall(pj.Call):
    def __init__(self, account):
        pj.Call.__init__(self, account)

    def onCallState(self, prm):
        try:
            ci = self.getInfo()
            logging.info(f"Estado da chamada: {ci.stateText}, código de status: {ci.lastStatusCode}")
        except pj.Error as e:
            logging.error(f"Erro ao obter estado da chamada: {e}")

class SipCall:
    def __init__(self, username, password, server, use_tls=False):
        self.ep = pj.Endpoint()
        logging.info("Criando endpoint no SIP Server FreePBX15...")
        self.ep.libCreate()

        # Configuração do endpoint
        ep_cfg = pj.EpConfig()
        ep_cfg.uaConfig.threadCnt = 1
        ep_cfg.logConfig.level = 5
        ep_cfg.logConfig.cb = self.log_cb
        ep_cfg.medConfig.noAudio = True
        ep_cfg.medConfig.sndAutoCloseTime = 0
        ep_cfg.medConfig.ipv6Use = 0  # Força IPv4 para evitar problemas

        logging.info("Inicializando endpoint ou FreePBX15 ...")
        self.ep.libInit(ep_cfg)

        # Configuração do transporte
        transport_cfg = pj.TransportConfig()
        transport_cfg.port = 5061 if use_tls else 0  # 5061 para TLS, 0 para UDP automático
        transport_cfg.boundAddr = "0.0.0.0"
        transport_type = pj.PJSIP_TRANSPORT_TLS if use_tls else pj.PJSIP_TRANSPORT_UDP
        if use_tls:
            transport_cfg.tlsConfig.verifyServer = False  # Para testes
        logging.info(f"Criando transporte {'TLS' if use_tls else 'UDP'}...")
        self.transport = self.ep.transportCreate(transport_type, transport_cfg)

        logging.info("Iniciando biblioteca do PJSIP PJSUA ...")
        self.ep.libStart()

        # Configuração da conta SIP
        acc_cfg = pj.AccountConfig()
        acc_cfg.idUri = f"sips:{username}@{server}" if use_tls else f"sip:{username}@{server}"
        acc_cfg.regConfig.registrarUri = f"sips:{server}" if use_tls else f"sip:{server}"
        cred = pj.AuthCredInfo("digest", server, username, 0, password)
        acc_cfg.sipConfig.authCreds.append(cred)

        logging.info("Criando conta SIP no servidor SIP FreePBX15...")
        self.account = pj.Account()
        self.account.create(acc_cfg)

        logging.info("Aguardando registro...")
        time.sleep(5)
        self.call = None

    def log_cb(self, level, str_data, len_data):
        logging.info(f"PJSIP: {str_data.strip()}")

    def make_call(self, dest_uri=None):
        if not dest_uri:
            dest_uri = f"sip:1203@192.168.1.240"  # Ramal 1203 do Raspberrry que será chamado ..Padrão
        if self.call and self.call.isActive():
            logging.warning("Chamada ativa detectada. Ramal 1202 (Ubuntu) chama raml 1203(ioT_ Encerrando antes de iniciar nova chamada...")
            self.terminate_call()

        self.call = MyCall(self.account)
        call_param = pj.CallOpParam(True)
        call_param.opt.audioCount = 0
        call_param.opt.videoCount = 0
        call_param.opt.flag = pj.PJSUA_CALL_NO_SDP_OFFER  # Evita SDP no INVITE
        logging.info(f"Iniciando chamada do UBUNTU 22.04 (ramal origem) para o IoT ramal:  {dest_uri}")
        try:
            self.call.makeCall(dest_uri, call_param)
        except pj.Error as e:
            logging.error(f"Erro ao iniciar chamada do FreePBX15 A: {e}")
            self.call = None

    def run(self):
        logging.info("Rodando loop de eventos para FreePBX15...")
        self.make_call()
        try:
            for _ in range(500):  # ~15 segundos
                self.ep.libHandleEvents(10)
                time.sleep(0.03)
        except Exception as e:
            logging.error(f"Erro no loop de eventos FreePBX15 B: {e}")
        finally:
            self.terminate()

    def terminate_call(self):
        if self.call and self.call.isActive():
            try:
                call_param = pj.CallOpParam()
                call_param.statusCode = pj.PJSIP_SC_DECLINE
                self.call.hangup(call_param)
                time.sleep(1)
                logging.info("Chamada para o FreePBX15 encerrada com sucesso.")
            except pj.Error as e:
                logging.warning(f"Erro ao encerrar chamada do FreePBX15: {e}")

    def terminate(self):
        logging.info("Encerrando a biblioteca PJSIP ...")
        self.terminate_call()
        try:
            self.ep.libDestroy()
            logging.info("Biblioteca PJSUA2 FreePBX15 destruída.")
        except pj.Error as e:
            logging.error(f"Erro ao destruir biblioteca FreePBX15: {e}")

if __name__ == "__main__":
    USERNAME = "1202"
    PASSWORD = "1202"
    SERVER = "192.168.1.240"

    # Use use_tls=True para protocol TLS, False para protocol UDP
    sip_call = SipCall(USERNAME, PASSWORD, SERVER, use_tls=False)
    try:
        sip_call.run()
    except KeyboardInterrupt:
        logging.info("Interrupção pelo usuário do LAB Mestrado detectada.")
        sip_call.terminate()
    except Exception as e:
        logging.error(f"Erro inesperado FreePBX15 D: {e}")
        sip_call.terminate()
