import asyncio
import logging

from ulpf_queue.consumer import KafkaConsumerWorker


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)


if __name__ == "__main__":
    asyncio.run(KafkaConsumerWorker().run_forever())
