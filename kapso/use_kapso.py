from .utils import normalize_kapso_webhook, extract_message_ids_from_webhook, mark_whatsapp_messages_as_read_batch, mark_whatsapp_messages_as_read, disable_typing_indicator
from .message_deduplicator import message_deduplicator
import logging
from models import User, ConversationConfig, UserMetadata
import os
import asyncio
from .data_loader import get_context_with_history
from agent.ask_agent import ask_agent_logic
from api.models import AskRequest
from .client import KapsoClient

logger = logging.getLogger(__name__)

async def use_kapso(webhook_data: dict, agent: str = "cedamoney"):
    """
    Procesa webhooks de Kapso para manejar mensajes entrantes de WhatsApp
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

async def handle_response(data_list: list, is_demo: bool = True) -> dict:
    """
    Maneja la respuesta del agente usando KapsoClient y ask_agent_logic
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
            combined_message_parts.append(message_content)
            logger.info("✅ Mensaje %d agregado a combined_message_parts", i)
        else:
            logger.warning("⚠️ Mensaje %d NO agregado: contenido vacío después de strip (tipo: '%s')", i, message_type)

    # Usamos el último mensaje o combinamos si es necesario (por ahora tomamos el texto completo)
    combined_message = " ".join(combined_message_parts)
    
    if not combined_message:
        return {"status": "success", "message": "Mensajes sin contenido omitidos"}
    
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
    
    # --- INVOCAR AGENTE Y RESPONDER ---
    if combined_message and whatsapp_conversation_id:
        logger.info("🤖 Consultando agente con query: '%s'", combined_message)
        
        # Ejecutar lógica del agente (síncrona) en un thread pool
        loop = asyncio.get_event_loop()
        
        def _run_agent():
            req = AskRequest(query=combined_message)
            return ask_agent_logic(req)
            
        try:
            agent_response = await loop.run_in_executor(None, _run_agent)
            
            # Enviar respuesta vía KapsoClient (síncrono) en thread pool
            def _send_replies():
                with KapsoClient() as kapso:
                    # Enviar respuesta de texto
                    kapso.send_message(whatsapp_conversation_id, agent_response.response)
                    
                    # Enviar detalles de productos si existen
                    if agent_response.items:
                        products_text = "Encontré estos productos:\n\n"
                        for item in agent_response.items[:3]:
                            products_text += f"*{item.title}*\nPrecio: ${item.price}\n{item.why}\n\n"
                        kapso.send_message(whatsapp_conversation_id, products_text)
            
            await loop.run_in_executor(None, _send_replies)
            logger.info("✅ Respuesta del agente enviada a conversación %s", whatsapp_conversation_id)
            
        except Exception as e:
            logger.error("❌ Error ejecutando agente o enviando respuesta: %s", e)
            import traceback
            logger.error("❌ Traceback: %s", traceback.format_exc())

    return {
        "status": "success",
        "message": "Respuesta enviada",
        "data": data_list
    }
