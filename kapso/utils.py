from typing import Dict, Any, List
import logging

logger = logging.getLogger(__name__)

def normalize_kapso_webhook(webhook_data: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Normaliza el webhook de Kapso a una estructura común.
    
    Soporta dos formatos:
    1. Formato antiguo: data[].message, data[].conversation, etc. en estructura plana
    2. Formato nuevo (batch): data[].message con campos anidados, data[].conversation, data[].whatsapp_config
    3. Formato raw/CloudAPI: data[].message con campos como 'type', 'text.body', 'kapso', etc.
    
    Args:
        webhook_data: Datos del webhook de Kapso
        
    Returns:
        Lista de mensajes normalizados con estructura común:
        [
            {
                "message": {
                    "id": "...",
                    "message_type": "text",
                    "content": "...",
                    ...
                },
                "conversation": {...},
                "whatsapp_config": {...},
                "is_new_conversation": bool
            },
            ...
        ]
    """
    if not webhook_data:
        logger.warning("⚠️ webhook_data vacío")
        return []
    
    data_list = webhook_data.get("data", [])
    if not data_list:
        logger.warning("⚠️ No hay 'data' en webhook_data")
        return []
    
    normalized_list = []
    
    for item in data_list:
        message_data = item.get("message", {})
        if not isinstance(message_data, dict):
            message_data = {}
            
        conversation_data = item.get("conversation", {})
        whatsapp_config_data = item.get("whatsapp_config", {})
        is_new_conversation = item.get("is_new_conversation", False)
        
        # --- Normalización del mensaje ---
        normalized_message = message_data.copy()
        
        # 1. Normalizar 'message_type'
        # Si falta 'message_type' pero existe 'type', usarlo (formato raw)
        if "message_type" not in normalized_message and "type" in normalized_message:
            normalized_message["message_type"] = normalized_message["type"]
            
        # 2. Normalizar 'content'
        # Si falta 'content', intentar extraerlo según el tipo
        if "content" not in normalized_message:
            msg_type = normalized_message.get("message_type", "")
            
            if msg_type == "text":
                # En formato raw, el texto está en message['text']['body']
                text_data = normalized_message.get("text", {})
                if isinstance(text_data, dict):
                    normalized_message["content"] = text_data.get("body", "")
            
            # TODO: Agregar soporte para otros tipos si es necesario (image, etc.)
            # Por ahora nos enfocamos en texto que es lo crítico
            
        # --- Fin normalización mensaje ---
        
        # --- Normalización de IDs y Config ---
        # Intentar extraer phone_number_id del item raíz o de conversation
        phone_number_id = item.get("phone_number_id") or conversation_data.get("phone_number_id")
        
        # Si conversation data tiene 'kapso' metadata (formato raw), a veces el ID de conv está ahí o es el del item
        if "id" not in conversation_data and "conversation_id" in item.get("batch_info", {}):
            conversation_data["id"] = item.get("batch_info", {}).get("conversation_id")
             
        # Asegurar whatsapp_config
        if not whatsapp_config_data:
            whatsapp_config_data = {}
             
        # Si falta display_phone_number_normalized, usar phone_number_id como fallback
        if "display_phone_number_normalized" not in whatsapp_config_data and phone_number_id:
            whatsapp_config_data["display_phone_number_normalized"] = str(phone_number_id)
             
        # Si falta whatsapp_config_id en conversation, intentar usar phone_number_id como fallback
        if "whatsapp_config_id" not in conversation_data:
            if phone_number_id:
                conversation_data["whatsapp_config_id"] = phone_number_id
            elif whatsapp_config_data.get("id"):
                conversation_data["whatsapp_config_id"] = whatsapp_config_data.get("id")
                 
        # Si falta reached_from_phone_number en whatsapp_config, intentar obtenerlo de conversation.phone_number_id
        # (aunque phone_number_id no es el número en sí, es un ID, pero es lo mejor que tenemos si falta lo otro)
        # pipeline.py lo usará para el config.
        
        normalized_item = {
            "message": normalized_message,
            "conversation": conversation_data,
            "whatsapp_config": whatsapp_config_data,
            "is_new_conversation": is_new_conversation,
            "phone_number_id": phone_number_id # Extra field for pipeline fallback
        }
        
        normalized_list.append(normalized_item)
    
    logger.info("✅ Webhook normalizado: %d mensaje(s) procesado(s)", len(normalized_list))
    return normalized_list