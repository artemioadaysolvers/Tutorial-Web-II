class CosmosStore:
    def __init__(self, endpoint, key, database, container):
        from azure.cosmos import CosmosClient
        self.client = CosmosClient(endpoint, credential=key)
        self.container = self.client.get_database_client(database).get_container_client(container)
    def list(self, owner):
        rows = list(self.container.query_items(query='SELECT c.id,c.body,c.created FROM c WHERE c.owner = @owner', parameters=[{'name':'@owner','value':owner}], partition_key=owner))
        return sorted(rows, key=lambda n:n['created'], reverse=True)
    def save(self, note):
        self.container.create_item(note)
    def delete(self, owner, id):
        from azure.cosmos.exceptions import CosmosResourceNotFoundError
        try:
            self.container.delete_item(id, partition_key=owner)
            return True
        except CosmosResourceNotFoundError:
            return False
    def health(self):
        self.container.read()
