from .utils import normalize_kapso_webhook, extract_message_ids_from_webhook, mark_whatsapp_messages_as_read_batch, mark_whatsapp_messages_as_read, disable_typing_indicator
from .message_deduplicator import message_deduplicator
import logging
from models import User, ConversationConfig, UserMetadata

logger = logging.getLogger(__name__)

async def use_kapso(webhook_data: dict, agent: str = "sofia"):
    """
    Procesa webhooks de Kapso para manejar mensajes entrantes de WhatsApp
    
    Solo responde con el agente a webhooks de tipo "whatsapp.message.received".
    Otros tipos de webhook (status, delivery, etc.) son confirmados pero no procesados.
    
    NUEVO: Incluye deduplicación automática para evitar respuestas duplicadas.
    
    Args:
        webhook_data (dict): Datos del webhook de Kapso
        
    Returns:
        dict: Resultado del procesamiento
    """
    try:
        webhook_type = webhook_data.get("type", "unknown")
        
        logger.info("🔍 Webhook recibido de Kapso - Tipo: %s", webhook_type)
        
        # Solo procesar mensajes entrantes con respuesta del agente
        if webhook_type == "whatsapp.message.received":
            # Normalizar webhook (soporta formato antiguo y nuevo)
            data_list = normalize_kapso_webhook(webhook_data)
            
            if not data_list:
                logger.warning("⚠️ No se pudo normalizar el webhook o está vacío")
                return {
                    "status": "success",
                    "message": "Webhook sin datos válidos",
                    "processed": False,
                    "agent_response": False
                }
            
            # NUEVO: Verificar deduplicación antes de procesar
            message_ids = extract_message_ids_from_webhook(webhook_data)
            logger.info("🔍 Message IDs: %s", message_ids)
            
            if message_ids and message_deduplicator.are_messages_already_processed(message_ids):
                logger.warning("⚠️ Mensaje DUPLICADO detectado y descartado: %s", message_ids)
                return {
                    "status": "success",
                    "message": "Webhook duplicado - mensajes ya procesados",
                    "processed": False,
                    "agent_response": False,
                    "duplicate": True,
                    "message_ids": message_ids
                }
            
            
            message_deduplicator.mark_messages_as_processed(message_ids)
            
            result = await handle_response(data_list=data_list)
            
            return result


    except Exception as e:
        logger.error("❌ Error procesando webhook de Kapso: %s: %s", type(e).__name__, str(e))
        import traceback
        logger.error("❌ Traceback: %s", traceback.format_exc())
        return {"status": "error", "message": "Error interno del servidor"}

async def handle_response(data_list: list) -> dict:
    """
    Maneja la respuesta del agente
    """
    first_data = data_list[0]
    conversation = first_data.get("conversation", {})
    reached_from_phone_number = first_data.get("whatsapp_config", {}).get("display_phone_number_normalized")
    
    if (reached_from_phone_number is None) and (os.getenv("ENVIRONMENT") in ("staging", "local")):
        reached_from_phone_number = "56920403095"
        logger.info("📞 Usando número default para staging/local: %s", reached_from_phone_number)
    phone_number = conversation.get("phone_number", None)
    whatsapp_conversation_id = conversation.get("id", None)
    contact_name = conversation.get("contact_name", "Usuario")
    whatsapp_config_id = conversation.get("whatsapp_config_id")
    whatsapp_config_id = conversation.get("whatsapp_config_id")
    if not whatsapp_config_id:
        # Intentar usar phone_number_id como fallback si parser lo extrajo
        whatsapp_config_id = first_data.get("phone_number_id")
            
    if not whatsapp_config_id:
        logger.warning("⚠️ whatsapp_config_id es None. Usando 'UNKNOWN_CONFIG'")
        whatsapp_config_id = "UNKNOWN_CONFIG"
    

    # Combinar mensajes
    combined_message_parts = []
    message_ids = []
    logger.info("📨 Procesando data_list con %d elemento(s)", len(data_list))
    
    for i, data in enumerate(data_list, 1):
        
        
        message_data = data.get("message", {})
        
        msg_id = message_data.get("id", None)
        message_ids.append(msg_id)
        
        message_type = message_data.get("message_type", "").lower()
        message_content_raw = message_data.get("content", "")
        message_content = message_content_raw.strip() if message_content_raw else ""
        
        
        if message_type in ("reaction", "sticker", "image"):
            logger.info("⏭️ Omitiendo mensaje %d: tipo '%s' está en lista de filtros", i, message_type)
            continue
        
        if message_content:
            combined_message_parts.append(f"[Mensaje {i}]: {message_content}")
            logger.info("✅ Mensaje %d agregado a combined_message_parts", i)
        else:
            logger.warning("⚠️ Mensaje %d NO agregado: contenido vacío después de strip (tipo: '%s')", i, message_type)

    processed_messages_count = len(combined_message_parts)
    
    if not combined_message_parts:
        return {"status": "success", "message": "Mensajes sin contenido omitidos"}
    
    combined_message = (f"El cliente envió {processed_messages_count} mensajes:\n\n" + "\n\n".join(combined_message_parts)) if processed_messages_count > 1 else combined_message_parts[0]
    
    try:
        await mark_whatsapp_messages_as_read_batch(message_ids, enable_typing_on_last=True, background_processing=False)
    except Exception as e:
        logger.error("❌ Error marcando mensajes como leídos: %s", e)
        
    user = User(
            name=contact_name,
            phone_number=phone_number,
            conversation_id=whatsapp_conversation_id,
            metadata=UserMetadata(whatsapp_config_id=whatsapp_config_id, reached_from_phone_number=reached_from_phone_number)
        )
    config = ConversationConfig(
        reached_from_phone_number=reached_from_phone_number,
        whatsapp_conversation_id=whatsapp_conversation_id,
        whatsapp_config_id=whatsapp_config_id,
        phone_number=phone_number,
        contact_name=contact_name,
        is_new_conversation=first_data.get("is_new_conversation", False),
    )
    
    conversation_history = None
    if is_demo:
        try:
            if whatsapp_conversation_id:
                context = await get_context_with_history(user, message_limit=20, is_testing=config.is_testing if hasattr(config, 'is_testing') else False)
                conversation_history = context.conversation_history
                logger.info("📚 Historial cargado para modo demo: %d mensajes", len(conversation_history) if conversation_history else 0)
        except Exception as e:
            logger.warning("⚠️ No se pudo cargar historial para contexto: %s", e)


    
        

    return {
        "status": "success",
        "message": "Respuesta del agente",
        "data": data_list
    }