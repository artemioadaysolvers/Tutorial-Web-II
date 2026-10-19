import unittest
from unittest.mock import Mock, patch
from store import CosmosStore
from azure.cosmos.exceptions import CosmosResourceNotFoundError

class CosmosTests(unittest.TestCase):
    def setUp(self):
        with patch('azure.cosmos.CosmosClient') as client:
            self.store=CosmosStore('https://example.test','secret','RecadosDB','recados')
            self.container=client.return_value.get_database_client.return_value.get_container_client.return_value
    def test_list_scoped_to_owner(self):
        self.container.query_items.return_value=[{'id':'1','body':'x','created':'2026-01-01'}]
        self.assertEqual(len(self.store.list('alice')),1)
        args=self.container.query_items.call_args.kwargs
        self.assertEqual(args['partition_key'],'alice')
        self.assertEqual(args['parameters'],[{'name':'@owner','value':'alice'}])
    def test_delete_scoped_to_owner(self):
        self.assertTrue(self.store.delete('bob','123'))
        self.container.delete_item.assert_called_once_with('123',partition_key='bob')
    def test_missing_item(self):
        self.container.delete_item.side_effect=CosmosResourceNotFoundError(status_code=404)
        self.assertFalse(self.store.delete('bob','123'))
