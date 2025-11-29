"""
A2A (Agent-to-Agent) Protocol Implementation
Enables inter-agent communication using message queues
"""
import asyncio
import json
from typing import Any, Dict, List, Optional, Callable
from datetime import datetime
import aio_pika
from aio_pika import Message, ExchangeType, DeliveryMode
from pydantic import BaseModel

from src.models.base import AgentMessage, MessageType
from config.settings import get_settings
from src.observability.monitor import get_logger


settings = get_settings()
logger = get_logger(__name__)


class A2AMessage(BaseModel):
    """A2A Protocol message format"""
    id: str
    protocol_version: str = "1.0"
    sender: str
    receiver: str
    message_type: str
    payload: Dict[str, Any]
    timestamp: str
    correlation_id: Optional[str] = None
    reply_to: Optional[str] = None


class AgentRegistry:
    """Registry of available agents for service discovery"""
    
    def __init__(self):
        self.agents: Dict[str, Dict[str, Any]] = {}
        self.logger = get_logger(__name__)
    
    def register(
        self,
        agent_id: str,
        agent_type: str,
        capabilities: List[str],
        endpoint: str
    ) -> None:
        """Register an agent"""
        self.agents[agent_id] = {
            "id": agent_id,
            "type": agent_type,
            "capabilities": capabilities,
            "endpoint": endpoint,
            "registered_at": datetime.utcnow().isoformat(),
            "status": "active"
        }
        
        self.logger.info(
            "agent_registered",
            agent_id=agent_id,
            agent_type=agent_type
        )
    
    def unregister(self, agent_id: str) -> bool:
        """Unregister an agent"""
        if agent_id in self.agents:
            del self.agents[agent_id]
            self.logger.info("agent_unregistered", agent_id=agent_id)
            return True
        return False
    
    def find_by_capability(self, capability: str) -> List[Dict[str, Any]]:
        """Find agents by capability"""
        return [
            agent for agent in self.agents.values()
            if capability in agent["capabilities"]
        ]
    
    def get_agent(self, agent_id: str) -> Optional[Dict[str, Any]]:
        """Get agent info"""
        return self.agents.get(agent_id)
    
    def list_all(self) -> List[Dict[str, Any]]:
        """List all registered agents"""
        return list(self.agents.values())


class A2AProtocol:
    """
    A2A Protocol Implementation
    Manages agent-to-agent communication via RabbitMQ
    """
    
    def __init__(self):
        self.settings = get_settings()
        self.logger = get_logger(__name__)
        self.connection: Optional[aio_pika.Connection] = None
        self.channel: Optional[aio_pika.Channel] = None
        self.exchange: Optional[aio_pika.Exchange] = None
        self.registry = AgentRegistry()
        self.message_handlers: Dict[str, Callable] = {}
        self._consumer_tasks: List[asyncio.Task] = []
    
    async def connect(self) -> None:
        """Establish connection to message broker"""
        if not self.settings.a2a_enabled:
            self.logger.warning("a2a_disabled")
            return
        
        try:
            self.connection = await aio_pika.connect_robust(
                self.settings.rabbitmq_url
            )
            
            self.channel = await self.connection.channel()
            await self.channel.set_qos(prefetch_count=10)
            
            # Declare exchange
            self.exchange = await self.channel.declare_exchange(
                self.settings.rabbitmq_exchange,
                ExchangeType.TOPIC,
                durable=True
            )
            
            self.logger.info(
                "a2a_connected",
                exchange=self.settings.rabbitmq_exchange
            )
            
        except Exception as e:
            self.logger.error(
                "a2a_connection_failed",
                error=str(e),
                exc_info=True
            )
            raise
    
    async def disconnect(self) -> None:
        """Close connection to message broker"""
        # Cancel consumer tasks
        for task in self._consumer_tasks:
            task.cancel()
        
        if self.connection:
            await self.connection.close()
            self.logger.info("a2a_disconnected")
    
    async def register_agent(
        self,
        agent_id: str,
        agent_type: str,
        capabilities: List[str],
        message_handler: Callable
    ) -> None:
        """Register an agent for A2A communication"""
        
        # Register in service registry
        self.registry.register(
            agent_id=agent_id,
            agent_type=agent_type,
            capabilities=capabilities,
            endpoint=f"{self.settings.rabbitmq_queue_prefix}{agent_id}"
        )
        
        # Store message handler
        self.message_handlers[agent_id] = message_handler
        
        # Create queue for agent
        queue_name = f"{self.settings.rabbitmq_queue_prefix}{agent_id}"
        queue = await self.channel.declare_queue(
            queue_name,
            durable=True
        )
        
        # Bind queue to exchange with routing key
        await queue.bind(
            self.exchange,
            routing_key=f"agent.{agent_type}.#"
        )
        
        # Start consuming messages
        consumer_task = asyncio.create_task(
            self._consume_messages(queue, agent_id)
        )
        self._consumer_tasks.append(consumer_task)
        
        self.logger.info(
            "agent_a2a_registered",
            agent_id=agent_id,
            queue=queue_name
        )
    
    async def send_message(
        self,
        sender: str,
        receiver: str,
        message_type: MessageType,
        payload: Dict[str, Any],
        correlation_id: Optional[str] = None
    ) -> str:
        """Send message to another agent"""
        
        message = A2AMessage(
            id=f"msg_{datetime.utcnow().timestamp()}",
            sender=sender,
            receiver=receiver,
            message_type=message_type.value,
            payload=payload,
            timestamp=datetime.utcnow().isoformat(),
            correlation_id=correlation_id
        )
        
        # Determine routing key
        receiver_agent = self.registry.get_agent(receiver)
        if receiver_agent:
            routing_key = f"agent.{receiver_agent['type']}.{receiver}"
        else:
            routing_key = f"agent.*.{receiver}"
        
        # Publish message
        await self.exchange.publish(
            Message(
                body=message.model_dump_json().encode(),
                delivery_mode=DeliveryMode.PERSISTENT,
                correlation_id=correlation_id,
                message_id=message.id
            ),
            routing_key=routing_key
        )
        
        self.logger.info(
            "a2a_message_sent",
            message_id=message.id,
            sender=sender,
            receiver=receiver,
            type=message_type.value
        )
        
        return message.id
    
    async def broadcast(
        self,
        sender: str,
        message_type: MessageType,
        payload: Dict[str, Any]
    ) -> str:
        """Broadcast message to all agents"""
        
        message = A2AMessage(
            id=f"msg_{datetime.utcnow().timestamp()}",
            sender=sender,
            receiver="*",
            message_type=message_type.value,
            payload=payload,
            timestamp=datetime.utcnow().isoformat()
        )
        
        # Broadcast to all agent types
        routing_key = "agent.#"
        
        await self.exchange.publish(
            Message(
                body=message.model_dump_json().encode(),
                delivery_mode=DeliveryMode.PERSISTENT,
                message_id=message.id
            ),
            routing_key=routing_key
        )
        
        self.logger.info(
            "a2a_broadcast_sent",
            message_id=message.id,
            sender=sender,
            type=message_type.value
        )
        
        return message.id
    
    async def _consume_messages(
        self,
        queue: aio_pika.Queue,
        agent_id: str
    ) -> None:
        """Consume messages from queue"""
        
        async with queue.iterator() as queue_iter:
            async for message in queue_iter:
                async with message.process():
                    try:
                        # Parse message
                        a2a_msg = A2AMessage.model_validate_json(
                            message.body.decode()
                        )
                        
                        self.logger.info(
                            "a2a_message_received",
                            message_id=a2a_msg.id,
                            receiver=agent_id,
                            sender=a2a_msg.sender
                        )
                        
                        # Handle message
                        handler = self.message_handlers.get(agent_id)
                        if handler:
                            await handler(a2a_msg)
                        else:
                            self.logger.warning(
                                "no_handler_for_agent",
                                agent_id=agent_id
                            )
                        
                    except Exception as e:
                        self.logger.error(
                            "message_processing_failed",
                            error=str(e),
                            exc_info=True
                        )
    
    async def request_reply(
        self,
        sender: str,
        receiver: str,
        request_payload: Dict[str, Any],
        timeout: int = 30
    ) -> Optional[Dict[str, Any]]:
        """Send request and wait for reply (RPC pattern)"""
        
        correlation_id = f"corr_{datetime.utcnow().timestamp()}"
        
        # Create callback queue for reply
        callback_queue = await self.channel.declare_queue(
            exclusive=True
        )
        
        # Send request
        await self.send_message(
            sender=sender,
            receiver=receiver,
            message_type=MessageType.REQUEST,
            payload=request_payload,
            correlation_id=correlation_id
        )
        
        # Wait for reply
        try:
            async with asyncio.timeout(timeout):
                async with callback_queue.iterator() as queue_iter:
                    async for message in queue_iter:
                        if message.correlation_id == correlation_id:
                            async with message.process():
                                reply = A2AMessage.model_validate_json(
                                    message.body.decode()
                                )
                                return reply.payload
        except asyncio.TimeoutError:
            self.logger.warning(
                "request_reply_timeout",
                correlation_id=correlation_id
            )
            return None
    
    def get_registered_agents(self) -> List[Dict[str, Any]]:
        """Get list of registered agents"""
        return self.registry.list_all()


# Global A2A protocol instance
a2a_protocol = A2AProtocol()


# ============================================================================
# EXAMPLE AGENT A2A IMPLEMENTATION
# ============================================================================

class A2AEnabledAgent:
    """Example of an agent with A2A capabilities"""
    
    def __init__(self, agent_id: str, agent_type: str, capabilities: List[str]):
        self.agent_id = agent_id
        self.agent_type = agent_type
        self.capabilities = capabilities
        self.logger = get_logger(f"agent.{agent_id}")
    
    async def start(self):
        """Start agent with A2A"""
        await a2a_protocol.connect()
        await a2a_protocol.register_agent(
            agent_id=self.agent_id,
            agent_type=self.agent_type,
            capabilities=self.capabilities,
            message_handler=self.handle_message
        )
        self.logger.info("agent_started_with_a2a")
    
    async def handle_message(self, message: A2AMessage):
        """Handle incoming A2A message"""
        self.logger.info(
            "message_received",
            message_id=message.id,
            sender=message.sender,
            type=message.message_type
        )
        
        # Process message based on type
        if message.message_type == MessageType.REQUEST.value:
            await self._handle_request(message)
        elif message.message_type == MessageType.EVENT.value:
            await self._handle_event(message)
    
    async def _handle_request(self, message: A2AMessage):
        """Handle request message"""
        # Process request and send reply
        reply_payload = {
            "status": "processed",
            "result": "Request processed successfully"
        }
        
        await a2a_protocol.send_message(
            sender=self.agent_id,
            receiver=message.sender,
            message_type=MessageType.RESPONSE,
            payload=reply_payload,
            correlation_id=message.correlation_id
        )
    
    async def _handle_event(self, message: A2AMessage):
        """Handle event message"""
        self.logger.info("event_received", event=message.payload)
    
    async def send_to_agent(self, receiver: str, payload: Dict[str, Any]):
        """Send message to another agent"""
        await a2a_protocol.send_message(
            sender=self.agent_id,
            receiver=receiver,
            message_type=MessageType.REQUEST,
            payload=payload
        )
    
    async def broadcast_event(self, event_data: Dict[str, Any]):
        """Broadcast event to all agents"""
        await a2a_protocol.broadcast(
            sender=self.agent_id,
            message_type=MessageType.EVENT,
            payload=event_data
        )
