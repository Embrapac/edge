import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import asyncio
import unittest

from data_aggregator.aggregator import ActuatorEvent, DataAggregator
from data_aggregator.uart_subscriber import UARTPublisher


class FakeUARTPublisher:
    def __init__(self):
        self.calls = []

    def publish_command(self, operation: str, command: str) -> bool:
        self.calls.append((operation, command))
        return True


class TestActuatorFlow(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.detection_queue = asyncio.Queue()
        self.output_queue = asyncio.Queue()
        self.input_queue = asyncio.Queue()
        self.aggregator = DataAggregator(
            self.detection_queue,
            self.output_queue,
            input_queue=self.input_queue,
        )

    async def test_process_pubsub_event_enqueues_actuator_event(self):
        await self.aggregator.process_pubsub_event(
            {
                "operation": "control_cbelt",
                "parameters": {"command": "START", "origin": "ihm"},
            }
        )

        queued = await asyncio.wait_for(self.input_queue.get(), timeout=0.1)
        self.assertIsInstance(queued, ActuatorEvent)
        self.assertEqual(queued.operation, "control_cbelt")
        self.assertEqual(queued.command, "START")
        self.assertEqual(queued.parameters["origin"], "ihm")

    async def test_consume_input_events_sends_command_to_uart_publisher(self):
        publisher = FakeUARTPublisher()
        consumer = asyncio.create_task(self.aggregator.consume_input_events(publisher))

        await self.input_queue.put(
            ActuatorEvent(
                timestamp=None,
                operation="control_cbelt",
                command="STOP",
                parameters={},
            )
        )

        await asyncio.wait_for(self._wait_for_calls(publisher, 1), timeout=0.1)
        self.assertEqual(publisher.calls, [("control_cbelt", "STOP")])

        consumer.cancel()
        with self.assertRaises(asyncio.CancelledError):
            await consumer

    async def _wait_for_calls(self, publisher: FakeUARTPublisher, expected: int):
        while len(publisher.calls) < expected:
            await asyncio.sleep(0)


class TestUARTPublisherEncoding(unittest.TestCase):
    def test_known_named_command_is_encoded(self):
        self.assertEqual(
            UARTPublisher.resolve_command_payload("control_cbelt", "START"),
            "00010000",
        )

    def test_explicit_binary_command_is_forwarded(self):
        self.assertEqual(
            UARTPublisher.resolve_command_payload("any_operation", "01010101"),
            "01010101",
        )

    def test_unknown_command_returns_none(self):
        self.assertIsNone(
            UARTPublisher.resolve_command_payload("control_cbelt", "UNKNOWN"),
        )


if __name__ == "__main__":
    unittest.main()