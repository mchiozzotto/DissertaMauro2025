#include <pjsua-lib/pjsua.h>
#include <pjmedia-codec.h>  // Incluir o cabeçalho do codec Opus

#define THIS_FILE "installcIot32.c"

#define SIP_DOMAIN   "192.168.1.240"   // Endereço IP do servidor SIP
#define SIP_USER     "1203"            // Ramal ou número de extensão
#define SIP_PASSWD   "1203"        // Senha da conta SIP
#define SIP_TRANSPORT PJSIP_TRANSPORT_UDP // Usando transporte UDP, pode ser TCP ou TLS

/* Error handling macro */
#define CHECK(status) if (status != PJ_SUCCESS) { pjsua_perror(THIS_FILE, "Error", status); return status; }

/* Callback de eventos by library sob recepção de chamadas entrantes */
static void on_incoming_call(pjsua_acc_id acc_id, pjsua_call_id call_id,
			     pjsip_rx_data *rdata)
{
    pjsua_call_info ci;
    pjsua_call_get_info(call_id, &ci);

    PJ_LOG(3,(THIS_FILE, "Call incoming de %.*s!!",
	      (int)ci.remote_info.slen,
	      ci.remote_info.ptr));

    pjsua_call_answer(call_id, 200, NULL, NULL);
}

/* A funçao C abaixo faz a leitura do Novo valor de Bitrate, lendo o arquivo "newbirate.txt" */

int ler_bit_rate(const char *caminho_arquivo) {
    FILE *arquivo = fopen(caminho_arquivo, "r");
    if (arquivo == NULL) {
        perror("Erro ao abrir o arquivo");
        return -1; // Indica erro
    }
    int bit_rate;
    if (fscanf(arquivo, "%d", &bit_rate) != 1) {
        fprintf(stderr, "Erro ao ler o bit rate do arquivo\n");
        fclose(arquivo);
        return -1; // Indica erro
    }
    fclose(arquivo);    return bit_rate;   
}

/* TRECHO ABAIXO INSERIDO 11 MAR 25 tarde  */


/* Callback called by the library when call's state has changed */
static void on_call_state(pjsua_call_id call_id, pjsip_event *e)
{
    pjsua_call_info ci;
    PJ_UNUSED_ARG(e);
    pjsua_call_get_info(call_id, &ci);
    PJ_LOG(3,(THIS_FILE, "Call %d state=%.*s", call_id,(int)ci.state_text.slen, ci.state_text.ptr));
	
	/* Nova função Ler o "bit_Rate" novo que chegou - 13 Mar/25 abaixo:  */
	
	if (ci.state == PJSIP_INV_STATE_CONFIRMED) {
               // Chamada estabelecida, alterar para o Novo bit rate
        int novo_bit_rate = ler_bit_rate("/home/pi/Socketudp/newbitrate.txt"); 
		           // Esta é a pasta onde o SW "Captura" o newbitrate do SocketUDP
        if (novo_bit_rate > 0) {
            pjmedia_codec_param param;
            pj_status_t status;
            pjmedia_codec_id opus_id = pjmedia_codec_opus_id();
            status = pjmedia_codec_get_param(opus_id, &param);
            if (status == PJ_SUCCESS) {
                param.enc_param.opus_cfg.bitrate = novo_bit_rate;
                status = pjmedia_codec_set_param(opus_id, &param);
                if (status != PJ_SUCCESS) {
                    PJ_LOG(1,(app, "Erro ao definir o bit rate do Opus Bit: %s", pj_strerror(status)));
                } else {
                        PJ_LOG(3,(app, "Bit rate do Opus alterado p/ novo Valor: %i", novo_bit_rate));
                }
            } else {
                PJ_LOG(1,(app, "Erro ao obter os parâmetros do Opus Bitrate: %s", pj_strerror(status)));
            }
		}
	}

}

/* Callback called by the library when call's media state has changed */
static void on_call_media_state(pjsua_call_id call_id)
{
    pjsua_call_info ci;

    pjsua_call_get_info(call_id, &ci);
    if (ci.media_status == PJSUA_CALL_MEDIA_ACTIVE) {
        // When media is active, connect call to sound device.
        pjsua_conf_connect(ci.conf_slot, 0);
        pjsua_conf_connect(0, ci.conf_slot);
    }
}

/* Display error and exit application */
static void error_exit(const char *title, pj_status_t status)
{
    pjsua_perror(THIS_FILE, title, status);
    pjsua_destroy();
    exit(1);
}

/* TRECHO ACIMA INSERIDO 11 Mar tarde  */

/* Configurar prioridade do codec após inicialização */
pj_status_t configure_codecs()
{
    pj_status_t status;
    pjsua_codec_info codec_info[32];
    unsigned codec_count;
    
    // Obtém a lista de codecs disponíveis
    status = pjsua_enum_codecs(codec_info, &codec_count);
    if (status != PJ_SUCCESS) {
        PJ_LOG(1, (THIS_FILE, "Falha ao enumerar codecs"));
        return status;
    }

    // Itera sobre a lista de codecs e verifica se o Opus está disponível
    for (unsigned i = 0; i < codec_count; ++i) {
        PJ_LOG(3, (THIS_FILE, "Codec disponível: %s", codec_info[i].codec_id.ptr));

        // Definir prioridade máxima para o codec Opus
        if (strstr(codec_info[i].codec_id.ptr, "opus") != NULL) {
            PJ_LOG(3, (THIS_FILE, "Codec Opus Encontrado, definindo prioridade"));
            status = pjsua_codec_set_priority(&codec_info[i].codec_id, PJMEDIA_CODEC_PRIO_HIGHEST);
            if (status != PJ_SUCCESS) {
                PJ_LOG(1, (THIS_FILE, "Erro ao definir prioridade para Opus"));
                return status;
            }
        }
    }
    return PJ_SUCCESS;
}

int main()
{
    pjsua_acc_id acc_id;
    pjsua_config cfg;
    pjsua_acc_config acc_cfg;
    pj_status_t status;
    // pj_status_t status_audio;  
	 // 11Mar/25 - Debug: Novo inserido para identificar saida de audio e MIC, code abaixo not used
    pjsua_logging_config log_cfg;   // Variaveis de LOG adicionadas 2 linhas esta e abaixo
    pjsua_media_config media_cfg;

    /* Inicializando PJSUA primeiro */
    status = pjsua_create();
    CHECK(status);

    /* Configuração básica */
    pjsua_config_default(&cfg);
    cfg.cb.on_incoming_call = &on_incoming_call;
    cfg.cb.on_call_media_state = &on_call_media_state;  // NEW line
    cfg.cb.on_call_state = &on_call_state;  // NEW Line
    pjsua_logging_config_default(&log_cfg);  // 2 Linhas added para LOG
    pjsua_media_config_default(&media_cfg);

    // Define o nível de log detalhado ( nível 5)

    log_cfg.msg_logging = PJ_TRUE;     // Ativa a exibição de mensagens de log

    log_cfg.level = 5;                 // Define o nível de log para 5 (mais detalhado)

    log_cfg.console_level = 5;         // Define o nível de log no console para 5

    // Inicializa o PJSUA com as configuracoes de LOG Detalhado:
    status = pjsua_init(&cfg, &log_cfg, &media_cfg);
    CHECK(status);
    if (status != PJ_SUCCESS) error_exit("Erro na inicializacao pjsua_init()", status); // NEW Line

    /* Adicionando o transporte UDP (ou TCP/TLS se preferir) */

    pjsua_transport_config trans_cfg;
    pjsua_transport_config_default(&trans_cfg);
    trans_cfg.port = 5060;  // Porta SIP padrão

    status = pjsua_transport_create(SIP_TRANSPORT, &trans_cfg, NULL);
    CHECK(status);

    /* Inicializando contas SIP */
    pjsua_acc_config_default(&acc_cfg);
    
    // Configurando a conta SIP -- TRECHO abaixo diferente do Demo SIMPLE_PJSUA.C Register to SIP Server ...
    //
    char sip_uri[256];
    snprintf(sip_uri, sizeof(sip_uri), "sip:%s@%s", SIP_USER, SIP_DOMAIN);
    acc_cfg.id = pj_str(sip_uri);  // Definindo o URI da conta
    acc_cfg.reg_uri = pj_str("sip:" SIP_DOMAIN);  // Definindo o endereço IP do servidor SIP

    acc_cfg.cred_count = 1;
    acc_cfg.cred_info[0].realm = pj_str("*");
    acc_cfg.cred_info[0].username = pj_str(SIP_USER);  // Nome de usuário SIP
    acc_cfg.cred_info[0].data_type = PJSIP_CRED_DATA_PLAIN_PASSWD;
    acc_cfg.cred_info[0].data = pj_str(SIP_PASSWD);  // Senha da conta SIP


    //Desabilitar SRTP:
    pjsua_media_config_default(&media_cfg);
    //media_cfg.srtp_use = PJMEDIA_SRTP_DISABLED;

    // Adiciona a conta ao PJSIP
    status = pjsua_acc_add(&acc_cfg, PJ_TRUE, &acc_id);
    CHECK(status);
    if (status != PJ_SUCCESS) error_exit("Erro ao adicionar a Conta ao PJSIP", status); // NEW Line

    /* Inicia o PJSUA */
    status = pjsua_start();
    CHECK(status);
    if (status != PJ_SUCCESS) error_exit("Erro ao dar Starting no pjsua", status); // NEW Line


     /* Configura o codec Opus com a prioridade mais alta */
    status = configure_codecs();
    CHECK(status);

    /* Aguarda eventos (como chamadas) indefinidamente - Loop infinito de chamadas */
    for (;;) {
        char option[10];   // NEW Line no loop adicionadas -- h e q para sair....

	puts("Aperte 'h' to Hang up chamada VoIP, 'q' para sair_quit");
        if (fgets(option, sizeof(option), stdin) == NULL) {
            puts ("EOF enquanto reading stdin_teclado, vou sair Agora...");
            break;
            }
         if (option[0] == 'q')
            break;

 	 if (option[0] == 'h')
            pjsua_call_hangup_all();
 
        pjsua_handle_events(70);  // Delay para eventos 70 ms
    }

    /* Finalizando */
    pjsua_destroy();
    return 0;
}
