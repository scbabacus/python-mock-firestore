import aiounittest

from mockfirestore import AsyncMockFirestore
from mockfirestore._helpers import consume_async_iterable


class TestAsyncMockFirestore(aiounittest.AsyncTestCase):
    async def test_client_get_all(self):
        fs = AsyncMockFirestore()
        fs._data = {"foo": {"first": {"id": 1}, "second": {"id": 2}}}
        doc = fs.collection("foo").document("first")
        results = await consume_async_iterable(fs.get_all([doc]))
        returned_doc_snapshot = results[0].to_dict()
        expected_doc_snapshot = (await doc.get()).to_dict()
        self.assertEqual(returned_doc_snapshot, expected_doc_snapshot)

    async def test_client_collections(self):
        fs = AsyncMockFirestore()
        fs._data = {"foo": {"first": {"id": 1}, "second": {"id": 2}}, "bar": {}}
        collections = await consume_async_iterable(fs.collections())
        expected_collections = fs._data

        self.assertEqual(len(collections), len(expected_collections))
        for collection in collections:
            self.assertTrue(collection._path[0] in expected_collections)

    async def test_write_single(self):
        fs = AsyncMockFirestore()

        doc_id, datum = ("my_data_record", {"value": "Hello world!"})
        collection_path = "sample_collection"

        coll_ref = fs.collection(collection_path)
        doc_ref = coll_ref.document(doc_id)
        await doc_ref.set(datum)

        result = await doc_ref.get()
        assert result.exists
        assert result.to_dict() == datum

    async def test_write_batch(self):
        fs = AsyncMockFirestore()
        data = [
            ("foo", {"value": "Foo"}),
            ("bar", {"value": "Bar"}),
            ("baz", {"value": "Baz"})
        ]
        collection_path = "sample_collection"

        batch_store = fs.batch()
        coll_ref = batch_store.collection(collection_path)
        doc_ref_data = [(coll_ref.document(key), datum) for (key, datum) in data]

        # Batch write data
        for doc_ref, datum in doc_ref_data:
            batch_store.set(doc_ref, datum)
        await batch_store.commit()

        # Async sequential read
        for doc_ref, datum in doc_ref_data:
            result = await doc_ref.get()
            assert result.exists
            assert result.to_dict() == datum
