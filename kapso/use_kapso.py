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
            normalized_data_list = normalize_kapso_webhook(webhook_data)
            
            if not normalized_data_list:
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
            
            logger.info("✅ Mensaje NUEVO (no duplicado). Procesando con agente: %s", agent)
            message_deduplicator.mark_messages_as_processed(message_ids)
            
            adapter = select_agent(agent)
            logger.info("🧩 Adapter seleccionado: %s", type(adapter).__name__)
            
            logger.info("📦 Datos normalizados a procesar: %d items", len(normalized_data_list))
            
            result = await handle_response_common(data_list=normalized_data_list, agent_adapter=adapter, is_demo=False)
            logger.info("🏁 Resultado de handle_response_common: %s", result.get("status"))
            
            return result
        
        
        # Tipos de webhook desconocidos
        else:
            logger.warning("⚠️ Tipo de webhook no reconocido - revisar documentación de Kapso: %s", webhook_type)
            
            return {
                "status": "success", 
                "message": "Webhook no procesado",
                "processed": False,
                "agent_response": False,
                "note": "Tipo de webhook no reconocido - revisar documentación de Kapso"
            }

    except Exception as e:
        logger.error("❌ Error procesando webhook de Kapso: %s: %s", type(e).__name__, str(e))
        import traceback
        logger.error("❌ Traceback: %s", traceback.format_exc())
        return {"status": "error", "message": "Error interno del servidor"}

