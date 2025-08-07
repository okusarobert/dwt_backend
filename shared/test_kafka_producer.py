import pytest
from unittest.mock import patch, MagicMock
from shared.kafka_producer import KafkaProducer
import json

def test_send_adds_timestamp_and_message_id():
    with patch('shared.kafka_producer.Producer') as MockProducer:
        mock_producer = MockProducer.return_value
        producer = KafkaProducer(bootstrap_servers='dummy:9092')
        message = {'foo': 'bar'}
        producer.send('test-topic', message.copy())
        args, kwargs = mock_producer.produce.call_args
        sent = json.loads(args[1].decode())
        assert 'timestamp' in sent
        assert 'message_id' in sent
        assert sent['foo'] == 'bar'
        mock_producer.flush.assert_called_once()

def test_send_error_logging():
    with patch('shared.kafka_producer.Producer') as MockProducer:
        mock_producer = MockProducer.return_value
        mock_producer.produce.side_effect = Exception('fail')
        producer = KafkaProducer(bootstrap_servers='dummy:9092')
        with pytest.raises(Exception):
            producer.send('test-topic', {'foo': 'bar'})
        mock_producer.flush.assert_not_called() 