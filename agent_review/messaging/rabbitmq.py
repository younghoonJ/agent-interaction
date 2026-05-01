"""RabbitMQ transport for Agent Review.

Purpose:
    Set up durable exchanges and queues, publish JSON messages, and consume task/result queues.
Parameters:
    RabbitMQClient receives an AMQP URL and JSON-like message dictionaries.
Return Value:
    Public methods publish messages or register blocking consumers.
Raised Exceptions:
    RuntimeError: If pika is unavailable.
    ValueError: If a consumed message is not valid JSON.
Author:
    Codex (OpenAI), generated 2026-05-01.
"""

from __future__ import annotations

import json
from collections.abc import Callable, Mapping

EXCHANGE_TASKS = "agent.tasks"
EXCHANGE_RESULTS = "agent.results"
EXCHANGE_EVENTS = "agent.events"
EXCHANGE_DLX = "agent.dlx"
QUEUE_RESULTS = "agent.result.orchestrator"
QUEUE_DEAD = "agent.dead"
ROUTING_RESULT_ORCHESTRATOR = "result.orchestrator"
ROUTING_DEAD_TASK = "dead.task"


def queue_for_agent(agent: str) -> str:
    return f"agent.task.{agent}"


def routing_for_agent(agent: str) -> str:
    return f"task.{agent}"


class RabbitMQClient:
    """RabbitMQ client for durable task/result transport.

    Args:
        url: AMQP URL for the RabbitMQ broker.

    Returns:
        A connected client with a channel ready for setup or publish operations.

    Raises:
        RuntimeError: If the pika dependency is not installed.
        Exception: If the broker connection fails.

    Author:
        Codex (OpenAI), generated 2026-05-01.
    """

    def __init__(self, url: str) -> None:
        try:
            import pika
        except ImportError as exc:
            raise RuntimeError("RabbitMQ support requires the pinned pika dependency.") from exc

        self._pika = pika
        params = pika.URLParameters(url)
        params.heartbeat = 0
        params.blocked_connection_timeout = None
        self.connection = pika.BlockingConnection(params)
        self.channel = self.connection.channel()

    def setup(self, agents: list[str]) -> None:
        """Declare exchanges, queues, bindings, and dead-letter routing.

        Args:
            agents: Agent names to declare task queues for (e.g. ["agent_a", "agent_b"]).

        Returns:
            None.

        Raises:
            Exception: If RabbitMQ rejects a declaration or binding.
        """

        channel = self.channel
        channel.exchange_declare(EXCHANGE_TASKS, exchange_type="direct", durable=True)
        channel.exchange_declare(EXCHANGE_RESULTS, exchange_type="direct", durable=True)
        channel.exchange_declare(EXCHANGE_EVENTS, exchange_type="topic", durable=True)
        channel.exchange_declare(EXCHANGE_DLX, exchange_type="direct", durable=True)

        dead_letter_args = {
            "x-dead-letter-exchange": EXCHANGE_DLX,
            "x-dead-letter-routing-key": ROUTING_DEAD_TASK,
        }
        for agent in agents:
            q = queue_for_agent(agent)
            channel.queue_declare(q, durable=True, arguments=dead_letter_args)
            channel.queue_bind(q, EXCHANGE_TASKS, routing_for_agent(agent))
        channel.queue_declare(QUEUE_RESULTS, durable=True)
        channel.queue_declare(QUEUE_DEAD, durable=True)

        channel.queue_bind(QUEUE_RESULTS, EXCHANGE_RESULTS, ROUTING_RESULT_ORCHESTRATOR)
        channel.queue_bind(QUEUE_DEAD, EXCHANGE_DLX, ROUTING_DEAD_TASK)

    def publish_json(self, exchange: str, routing_key: str, payload: Mapping[str, object]) -> None:
        """Publish a persistent JSON message.

        Args:
            exchange: Exchange name.
            routing_key: Direct or topic routing key.
            payload: JSON-serializable mapping.

        Returns:
            None.

        Raises:
            TypeError: If payload cannot be serialized as JSON.
            Exception: If RabbitMQ publish fails.
        """

        body = json.dumps(dict(payload), ensure_ascii=False, sort_keys=True).encode("utf-8")
        properties = self._pika.BasicProperties(content_type="application/json", delivery_mode=2)
        self.channel.basic_publish(exchange=exchange, routing_key=routing_key, body=body, properties=properties)

    def consume_json(self, queue: str, callback: Callable[[dict[str, object]], None]) -> None:
        """Consume JSON messages with automatic ack after callback success.

        Args:
            queue: Queue name.
            callback: Function called with each decoded message.

        Returns:
            None. This method blocks until RabbitMQ consumption stops.

        Raises:
            ValueError: If a message body is not a JSON object.
            Exception: If RabbitMQ consumption fails.
        """

        def _handle_message(channel: object, method: object, properties: object, body: bytes) -> None:
            del properties
            data = json.loads(body.decode("utf-8"))
            if not isinstance(data, dict):
                raise ValueError("RabbitMQ JSON message must be an object.")
            callback(data)
            channel.basic_ack(delivery_tag=method.delivery_tag)

        self.channel.basic_qos(prefetch_count=1)
        self.channel.basic_consume(queue=queue, on_message_callback=_handle_message)
        self.channel.start_consuming()

    def close(self) -> None:
        """Close the RabbitMQ connection.

        Args:
            None.

        Returns:
            None.

        Raises:
            Exception: If the connection close operation fails.
        """

        self.connection.close()
