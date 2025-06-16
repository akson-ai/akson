"""This module contains the PubSub class for publishing and subscribing to topics.
In the FastAPI app, it is used for sending chat events to clients.
Topic corresponds to a chat ID.
"""

import asyncio
import contextlib
import uuid
from functools import partial
from typing import Any, AsyncIterator, Callable, Coroutine, Dict


class PubSub:
    def __init__(self):
        self._subscribers: Dict[str, Dict[str, Callable[[Any], Coroutine]]] = {}
        self._subscription_lock = asyncio.Lock()

    def get_publisher(self, topic: str) -> Callable[[Any], Coroutine]:
        return partial(self.publish, topic)

    async def publish(self, topic: str, message: Any) -> int:
        """
        Publish a message to a topic.

        Args:
            topic: The topic to publish to
            message: The message to publish

        Returns:
            Number of subscribers that received the message
        """
        if topic not in self._subscribers:
            return 0

        subscriber_count = 0
        pending_tasks = []

        # Create tasks for all subscriber callbacks
        for callback in self._subscribers[topic].values():
            pending_tasks.append(asyncio.create_task(callback(message)))
            subscriber_count += 1

        # Await all notifications to complete if there are any
        if pending_tasks:
            await asyncio.gather(*pending_tasks, return_exceptions=True)

        return subscriber_count

    @contextlib.asynccontextmanager
    async def subscribe(self, topic: str) -> AsyncIterator[asyncio.Queue]:
        """
        Subscribe to a topic using a context manager.

        Args:
            topic: The topic to subscribe to

        Returns:
            An asyncio Queue that will receive messages

        Example:
            async with pubsub.subscribe("my-topic") as queue:
                while True:
                    message = await queue.get()
                    # process message
        """
        queue = asyncio.Queue()
        subscription_id = await self._subscribe(topic, queue)

        try:
            yield queue
        finally:
            await self.unsubscribe(topic, subscription_id)

    async def _subscribe(self, topic: str, queue: asyncio.Queue) -> str:
        """
        Internal method to handle subscription logic.
        """

        async def callback(message: Any) -> None:
            await queue.put(message)

        subscription_id = str(uuid.uuid4())

        async with self._subscription_lock:
            if topic not in self._subscribers:
                self._subscribers[topic] = {}
            self._subscribers[topic][subscription_id] = callback

        return subscription_id

    async def unsubscribe(self, topic: str, subscription_id: str) -> bool:
        """
        Unsubscribe from a topic.

        Args:
            topic: The topic to unsubscribe from
            subscription_id: The subscription ID to remove

        Returns:
            True if successfully unsubscribed, False otherwise
        """
        async with self._subscription_lock:
            if topic not in self._subscribers:
                return False

            if subscription_id not in self._subscribers[topic]:
                return False

            del self._subscribers[topic][subscription_id]

            # Clean up empty topics
            if not self._subscribers[topic]:
                del self._subscribers[topic]

            return True


# Example usage
async def example_usage():
    pubsub = PubSub()

    # Publisher task
    async def publisher():
        for i in range(5):
            await asyncio.sleep(1)
            print(f"Publishing message {i}")
            subscribers = await pubsub.publish("example-topic", f"Message {i}")
            print(f"Message {i} delivered to {subscribers} subscribers")

    # Subscriber task
    async def subscriber(name: str):
        try:
            async with pubsub.subscribe("example-topic") as queue:
                while True:
                    message = await queue.get()
                    print(f"Subscriber {name} received: {message}")
        except asyncio.CancelledError:
            print(f"Subscriber {name} was cancelled")
            raise

    # Start the publisher and subscribers
    publisher_task = asyncio.create_task(publisher())

    subscriber_tasks = [
        asyncio.create_task(subscriber("A")),
        asyncio.create_task(subscriber("B")),
    ]

    # Wait for publisher to finish
    await publisher_task

    # Cancel subscribers after publisher is done
    for task in subscriber_tasks:
        task.cancel()

    await asyncio.gather(*subscriber_tasks, return_exceptions=True)


if __name__ == "__main__":
    asyncio.run(example_usage())
