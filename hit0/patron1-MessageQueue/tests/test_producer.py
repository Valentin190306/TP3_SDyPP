import sys
import os
import pytest
import pika
from unittest.mock import patch, MagicMock, call

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import producer


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_channel():
    mock_channel = MagicMock()
    mock_channel.queue_declare.return_value = None
    return mock_channel


# ---------------------------------------------------------------------------
# Tests de send_messages
# ---------------------------------------------------------------------------

def test_send_messages_declara_cola_correctamente():
    mock_channel = _make_channel()
    with patch('pika.BlockingConnection'):
        producer.send_messages(mock_channel)
    mock_channel.queue_declare.assert_called_once_with(
        queue='task_queue', durable=True
    )


def test_send_messages_envia_exactamente_10_mensajes():
    mock_channel = _make_channel()
    with patch('pika.BlockingConnection'):
        producer.send_messages(mock_channel)
    assert mock_channel.basic_publish.call_count == 10


def test_send_messages_formato_correcto_de_mensajes():
    mock_channel = _make_channel()
    with patch('pika.BlockingConnection'):
        producer.send_messages(mock_channel)
    bodies = [c.kwargs['body'] for c in mock_channel.basic_publish.call_args_list]
    expected = [f"Tarea {i}" for i in range(1, 11)]
    assert bodies == expected


def test_send_messages_delivery_mode_persistente():
    mock_channel = _make_channel()
    with patch('pika.BlockingConnection'):
        producer.send_messages(mock_channel)
    for c in mock_channel.basic_publish.call_args_list:
        properties = c.kwargs['properties']
        assert properties.delivery_mode == 2


def test_send_messages_respeta_count_personalizado():
    mock_channel = _make_channel()
    with patch('pika.BlockingConnection'):
        producer.send_messages(mock_channel, count=5)
    assert mock_channel.basic_publish.call_count == 5
    bodies = [c.kwargs['body'] for c in mock_channel.basic_publish.call_args_list]
    assert bodies == [f"Tarea {i}" for i in range(1, 6)]


# ---------------------------------------------------------------------------
# Tests de connect
# ---------------------------------------------------------------------------

def test_connect_reintenta_ante_fallo():
    mock_connection = MagicMock()
    side_effects = [
        pika.exceptions.AMQPConnectionError("fallo 1"),
        pika.exceptions.AMQPConnectionError("fallo 2"),
        mock_connection,
    ]
    with patch('pika.BlockingConnection', side_effect=side_effects) as mock_bc, \
         patch('time.sleep'):
        result = producer.connect()
    assert mock_bc.call_count == 3
    assert result is mock_connection


def test_connect_falla_despues_de_max_intentos():
    with patch(
        'pika.BlockingConnection',
        side_effect=pika.exceptions.AMQPConnectionError("sin broker"),
    ), patch('time.sleep'):
        with pytest.raises((RuntimeError, SystemExit)):
            producer.connect()
