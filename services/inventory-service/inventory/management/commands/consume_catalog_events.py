import json
import os
import logging
import time

time
import pika

from django.core.management.base import BaseCommand
from django.db import DatabaseError

from inventory.messaging.catalog_event import InvalidCatalogEvent, process_catalog_event


logger = logging.getLogger(__name__)

RABBITMQ_HOST = os.getenv('RABBITMQ_HOST', 'rabbitmq')
RABBITMQ_PORT = int(os.getenv('RABBITMQ_PORT', '5672'))

EXCHANGE_NAME = "catalog.events"
QUEUE_NAME = 'inventory.product-created'
ROUTING_KEY = "product.created"

DEAD_LETTER_EXCHANGE = 'catalog.events.dlx'
DEAD_LETTER_QUEUE = 'inventory.product-created.dlq'
DEAD_LETTER_ROUTING_KEY = 'product-created.invalid'


class Command(BaseCommand):
    help = "consume product.created events and initialize inventory records."

    def handle(self, *args, **options):
        self.stdout.write("starting the Catalog event consumer...")

        while True:
            connection = None

            try:
                connection = pika.BlockingConnection(pika.ConnectionParameters(
                    host=RABBITMQ_HOST, port=RABBITMQ_PORT, heartbeat=60, blocked_connection_timeout=30
                ))
                channel = connection.channel()
                self._declare_topology(channel)
                channel.basic_qos(prefetch_count=1)
                channel.basic_consume(queue=QUEUE_NAME, on_message_callback=self._on_message, auto_ack=False)

                self.stdout.write(self.style.SUCCESS(f"Waiting for `{ROUTING_KEY}` events on queue `{QUEUE_NAME}`."))
                channel.start_consuming()
            except KeyboardInterrupt:
                self.stdout.write("Stoping the catalog event consumer...")
                break
            except (pika.exceptions.AMQPError, OSError):
                self.stdout.write('Rabbitmq connection error or consumer error.')
                self.stdout.write('Rabbitmq unavailable, trying again in 5 seconds...')
                time.sleep(5)
            finally:
                if connection is not None and connection.is_open:
                    try:
                        connection.close()
                    except pika.exceptions.AMQPError:
                        self.stdout.write('Error closing rabbitmq connection.')

    @staticmethod
    def _declare_topology(channel: pika.adapters.blocking_connection.BlockingChannel):
        channel.exchange_declare(exchange=EXCHANGE_NAME, exchange_type='topic', durable=True)

        channel.exchange_declare(exchange=DEAD_LETTER_EXCHANGE, exchange_type='direct', durable=True)
        channel.queue_declare(queue=DEAD_LETTER_QUEUE, durable=True)
        channel.queue_bind(queue=DEAD_LETTER_QUEUE, exchange=DEAD_LETTER_EXCHANGE, routing_key=DEAD_LETTER_ROUTING_KEY)


        channel.queue_declare(queue=QUEUE_NAME, durable=True, arguments={
            "x-dead-letter-exchange": DEAD_LETTER_EXCHANGE,
            "x-dead-letter-routing-key": DEAD_LETTER_ROUTING_KEY,
        })
        channel.queue_bind(queue=QUEUE_NAME, exchange=EXCHANGE_NAME, routing_key=ROUTING_KEY)


    @staticmethod
    def _on_message(channel, method, properties, body):
        try:
            message = json.loads(body.decode('utf-8'))
            item, created = process_catalog_event(message)
        except (UnicodeDecodeError, json.JSONDecodeError, InvalidCatalogEvent) as exc:
            logger.info(f'rejecting invalid catalog event: {exc}')
            channel.basic_reject(delivery_tag=method.delivery_tag, requeue=False)  # send it straight to dead letter exchange
            return
        except DatabaseError as exc:
            logger.info(f'Database error while processing catalog event: {exc}')
            channel.basic_nack(delivery_tag=method.delivery_tag, requeue=True)  # it was a database error so requeue the message to try again
            return
        except Exception:
            logger.info('Unexpected error while processing catalog event')
            channel.basic_reject(delivery_tag=method.delivery_tag, requeue=False)
            return

        channel.basic_ack(delivery_tag=method.delivery_tag)

        if created:
            logger.info(f'Created inventory item for product_id: {item.product_id}, quantity: {item.quantity}')
        else:
            logger.info(f'Duplicat product.created event ignored for product_id: {item.product_id}')
